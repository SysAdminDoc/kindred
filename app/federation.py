"""ActivityPub-style public profiles and signed federation transport.

Federation is deliberately opt-in.  The actor representation contains only
the fields intended for a public profile; questionnaire answers, embeddings,
messages, credentials, and other private vault data never cross an instance
boundary.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import ipaddress
import json
import re
import secrets
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime, parsedate_to_datetime
from pathlib import Path
from typing import Mapping

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

from app.config import (
    FEDERATION_BASE_URL,
    FEDERATION_ENABLED,
    FEDERATION_FETCH_TIMEOUT_SECONDS,
    FEDERATION_KEY_PATH,
    FEDERATION_MAX_BODY_BYTES,
    FEDERATION_USER_AGENT,
)


ACTIVITYSTREAMS_CONTEXT = "https://www.w3.org/ns/activitystreams"
SECURITY_CONTEXT = "https://w3id.org/security/v1"
ACTIVITY_CONTENT_TYPES = "application/activity+json, application/ld+json"
PROFILE_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._~-]{0,127}$")


class FederationError(Exception):
    """Base error for a rejected or unavailable federation operation."""


class ActorResolutionError(FederationError):
    """Raised when a remote actor cannot be safely resolved."""


class SignatureVerificationError(FederationError):
    """Raised when an ActivityPub-style signed request is invalid."""


class DeliveryError(FederationError):
    """Raised when an activity cannot be delivered to a remote inbox."""


def enabled() -> bool:
    """Return whether federation has a complete local configuration."""
    return bool(FEDERATION_ENABLED and _base_url())


def _base_url() -> str:
    return FEDERATION_BASE_URL.rstrip("/")


def _base_host() -> str:
    return urllib.parse.urlsplit(_base_url()).hostname or ""


def _ensure_http_url(value: str, *, allow_local: bool = False) -> str:
    if not isinstance(value, str) or len(value) > 2048:
        raise ActorResolutionError("Federation URL is invalid")
    parsed = urllib.parse.urlsplit(value)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ActorResolutionError("Federation URL must use HTTP or HTTPS")
    if parsed.username or parsed.password or parsed.fragment:
        raise ActorResolutionError("Federation URL contains unsupported credentials or fragment")
    host = parsed.hostname.lower().rstrip(".")
    if not allow_local and _is_private_host(host):
        raise ActorResolutionError("Federation URL points to a private address")
    return urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, parsed.path, parsed.query, ""))


def _is_private_host(host: str) -> bool:
    if host in {"localhost", "localhost.localdomain"} or host.endswith(".local"):
        return True
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        return False
    return bool(
        address.is_private
        or address.is_loopback
        or address.is_link_local
        or address.is_reserved
        or address.is_unspecified
        or address.is_multicast
    )


def actor_url(profile_id: str) -> str:
    if not enabled() or not PROFILE_ID_PATTERN.fullmatch(str(profile_id)):
        raise FederationError("Federation is not configured for this profile")
    return f"{_base_url()}/users/{urllib.parse.quote(str(profile_id), safe='') }"


def inbox_url() -> str:
    if not enabled():
        raise FederationError("Federation is not enabled")
    return f"{_base_url()}/api/federation/inbox"


def outbox_url(profile_id: str) -> str:
    return f"{actor_url(profile_id)}/outbox"


def profile_id_from_actor(value: str) -> str | None:
    """Return a local profile id only for this instance's actor URL."""
    if not isinstance(value, str) or not enabled():
        return None
    expected_prefix = f"{_base_url()}/users/"
    if not value.startswith(expected_prefix):
        return None
    remainder = value[len(expected_prefix):]
    if "/" in remainder or not PROFILE_ID_PATTERN.fullmatch(remainder):
        return None
    return urllib.parse.unquote(remainder)


def _profile_value(profile: Mapping, field: str):
    privacy = profile.get("privacy")
    if isinstance(privacy, dict) and str(privacy.get(field, "")).lower() in {
        "private", "hidden", "none",
    }:
        return None
    return profile.get(field)


def _profile_interests(value) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip()[:100] for item in value if str(item).strip()][:25]
    if isinstance(value, str):
        return [item.strip()[:100] for item in value.split(",") if item.strip()][:25]
    return []


def _public_media_url(photo: str | None) -> str | None:
    if not photo or "/" in str(photo) or "\\" in str(photo):
        return None
    if not enabled():
        return None
    return f"{_base_url()}/uploads/{urllib.parse.quote(str(photo), safe='') }"


def _load_private_key() -> Ed25519PrivateKey:
    path = Path(FEDERATION_KEY_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        key = serialization.load_pem_private_key(path.read_bytes(), password=None)
        if not isinstance(key, Ed25519PrivateKey):
            raise FederationError("Federation key file is not an Ed25519 private key")
        return key
    key = Ed25519PrivateKey.generate()
    path.write_bytes(
        key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
    )
    try:
        path.chmod(0o600)
    except OSError:
        pass
    return key


def public_key_pem() -> str:
    key = _load_private_key().public_key()
    return key.public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("ascii")


def build_actor(profile: Mapping) -> dict:
    """Build the public actor document for a local profile."""
    profile_id = str(profile.get("id") or "")
    actor = actor_url(profile_id)
    result = {
        "@context": [ACTIVITYSTREAMS_CONTEXT, SECURITY_CONTEXT],
        "id": actor,
        "type": "Person",
        "url": actor,
        "preferredUsername": profile_id,
        "name": str(profile.get("name") or "Kindred member")[:200],
        "inbox": inbox_url(),
        "outbox": outbox_url(profile_id),
        "publicKey": {
            "id": f"{actor}#main-key",
            "owner": actor,
            "publicKeyPem": public_key_pem(),
        },
    }
    public_fields = {
        "summary": "about_me",
        "age": "age",
        "gender": "gender",
        "seeking": "seeking",
        "country": "country",
        "headline": "headline",
        "relationshipIntent": "relationship_intent",
        "datingEnergy": "dating_energy",
        "verified": "verified",
    }
    for output, field in public_fields.items():
        value = _profile_value(profile, field)
        if value not in (None, "", {}):
            result[output] = value
    interests = _profile_interests(_profile_value(profile, "interests"))
    if interests:
        result["attachment"] = [{"type": "PropertyValue", "name": "interests", "value": interests}]
    media_url = _public_media_url(_profile_value(profile, "photo"))
    if media_url:
        result["icon"] = {"type": "Image", "mediaType": "image/*", "url": media_url}
    return result


def build_webfinger(profile: Mapping) -> dict:
    profile_id = str(profile.get("id") or "")
    actor = actor_url(profile_id)
    return {
        "subject": f"acct:{profile_id}@{_base_host()}",
        "aliases": [actor],
        "links": [
            {"rel": "self", "type": ACTIVITY_CONTENT_TYPES.split(", ")[0], "href": actor},
            {"rel": "alternate", "type": "text/html", "href": actor},
        ],
    }


def _header(headers: Mapping[str, str], name: str) -> str:
    wanted = name.lower()
    for key, value in headers.items():
        if str(key).lower() == wanted:
            return str(value)
    return ""


def _signature_params(value: str) -> dict[str, str]:
    if not value.startswith("Signature "):
        raise SignatureVerificationError("Missing HTTP signature")
    params: dict[str, str] = {}
    for part in re.split(r",\s*", value[len("Signature "):]):
        key, separator, raw = part.partition("=")
        if not separator or not key:
            continue
        params[key.strip()] = raw.strip().strip('"')
    if not params.get("keyId") or not params.get("signature"):
        raise SignatureVerificationError("Incomplete HTTP signature")
    return params


def _request_target(url: str) -> str:
    parsed = urllib.parse.urlsplit(url)
    path = parsed.path or "/"
    return path + (f"?{parsed.query}" if parsed.query else "")


def _signing_string(method: str, url: str, headers: Mapping[str, str], names: list[str]) -> str:
    values = []
    for name in names:
        if name == "(request-target)":
            value = f"{method.lower()} {_request_target(url)}"
        else:
            value = _header(headers, name)
            if not value:
                raise SignatureVerificationError(f"Signed header {name} is missing")
        values.append(f"{name}: {value}")
    return "\n".join(values)


def build_signed_headers(method: str, url: str, body: bytes, actor: str) -> dict[str, str]:
    """Create headers for a signed ActivityPub-style HTTP request."""
    parsed = urllib.parse.urlsplit(url)
    now = format_datetime(datetime.now(timezone.utc), usegmt=True)
    digest = "SHA-256=" + base64.b64encode(hashlib.sha256(body).digest()).decode("ascii")
    headers = {
        "Host": parsed.netloc,
        "Date": now,
        "Digest": digest,
    }
    names = ["(request-target)", "host", "date", "digest"]
    signing = _signing_string(method, url, headers, names)
    signature = _load_private_key().sign(signing.encode("utf-8"))
    headers["Signature"] = (
        f'Signature keyId="{actor}#main-key",algorithm="ed25519-sha256",'
        f'headers="{" ".join(names)}",signature="'
        f'{base64.b64encode(signature).decode("ascii")}"'
    )
    return headers


def verify_incoming_signature(
    method: str,
    url: str,
    body: bytes,
    headers: Mapping[str, str],
    actor: Mapping,
    *,
    now: datetime | None = None,
) -> None:
    """Verify digest, freshness, key ownership, and Ed25519 HTTP signature."""
    if len(body) > FEDERATION_MAX_BODY_BYTES:
        raise SignatureVerificationError("Federation request body is too large")
    digest = _header(headers, "digest")
    expected_digest = "SHA-256=" + base64.b64encode(hashlib.sha256(body).digest()).decode("ascii")
    if not secrets.compare_digest(digest, expected_digest):
        raise SignatureVerificationError("Request digest does not match body")
    date_value = _header(headers, "date")
    try:
        signed_at = parsedate_to_datetime(date_value)
    except (TypeError, ValueError, IndexError, OverflowError) as exc:
        raise SignatureVerificationError("Invalid request date") from exc
    signed_at = signed_at.astimezone(timezone.utc)
    current = now or datetime.now(timezone.utc)
    if abs(current - signed_at) > timedelta(minutes=10):
        raise SignatureVerificationError("Stale federation request")
    params = _signature_params(_header(headers, "signature"))
    key_id = params["keyId"]
    actor_id = str(actor.get("id") or "")
    public_key = actor.get("publicKey")
    if not isinstance(public_key, Mapping):
        raise SignatureVerificationError("Remote actor has no public key")
    if key_id != str(public_key.get("id") or "") or str(public_key.get("owner") or "") != actor_id:
        raise SignatureVerificationError("Signature key is not owned by actor")
    names = params.get("headers", "").split()
    required = ["(request-target)", "host", "date", "digest"]
    if names != required:
        raise SignatureVerificationError("Unsupported signed header set")
    try:
        public = serialization.load_pem_public_key(str(public_key["publicKeyPem"]).encode("ascii"))
        if not isinstance(public, Ed25519PublicKey):
            raise TypeError
        signature = base64.b64decode(params["signature"], validate=True)
        public.verify(signature, _signing_string(method, url, headers, names).encode("utf-8"))
    except (ValueError, TypeError, KeyError, binascii.Error, InvalidSignature) as exc:
        raise SignatureVerificationError("Invalid remote signature") from exc


def _read_json(response) -> dict:
    content = response.read(FEDERATION_MAX_BODY_BYTES + 1)
    if len(content) > FEDERATION_MAX_BODY_BYTES:
        raise ActorResolutionError("Remote federation response is too large")
    try:
        value = json.loads(content.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ActorResolutionError("Remote federation response is not JSON") from exc
    if not isinstance(value, dict):
        raise ActorResolutionError("Remote federation response is not an object")
    return value


def _fetch_json(url: str) -> dict:
    safe_url = _ensure_http_url(url)
    request = urllib.request.Request(
        safe_url,
        headers={
            "Accept": ACTIVITY_CONTENT_TYPES,
            "User-Agent": FEDERATION_USER_AGENT,
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=FEDERATION_FETCH_TIMEOUT_SECONDS) as response:
            return _read_json(response)
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise ActorResolutionError("Remote federation host is unavailable") from exc


def _validate_actor(actor: Mapping, expected_id: str | None = None) -> dict:
    actor_id = _ensure_http_url(str(actor.get("id") or ""))
    if expected_id and actor_id != expected_id:
        raise ActorResolutionError("Remote actor id does not match the requested actor")
    if actor.get("type") not in {"Person", "Application", "Service"}:
        raise ActorResolutionError("Remote federation actor type is unsupported")
    inbox = _ensure_http_url(str(actor.get("inbox") or ""))
    public_key = actor.get("publicKey")
    if not isinstance(public_key, Mapping) or not public_key.get("publicKeyPem"):
        raise ActorResolutionError("Remote actor has no usable public key")
    key_id = str(public_key.get("id") or "")
    key_id_parts = urllib.parse.urlsplit(key_id)
    if (
        key_id_parts.scheme not in {"http", "https"}
        or not key_id_parts.hostname
        or key_id_parts.username
        or key_id_parts.password
        or not key_id.startswith(actor_id + "#")
    ):
        raise ActorResolutionError("Remote actor public key id is invalid")
    owner = _ensure_http_url(str(public_key.get("owner") or ""))
    if owner != actor_id:
        raise ActorResolutionError("Remote actor public key ownership is invalid")
    normalized = dict(actor)
    normalized.update({"id": actor_id, "inbox": inbox, "publicKey": dict(public_key)})
    if actor.get("outbox"):
        normalized["outbox"] = _ensure_http_url(str(actor["outbox"]))
    return normalized


def resolve_actor(reference: str) -> dict:
    """Resolve an actor URL or acct handle through WebFinger."""
    if not isinstance(reference, str) or len(reference.strip()) > 2048:
        raise ActorResolutionError("Remote actor reference is invalid")
    reference = reference.strip()
    if reference.lower().startswith("acct:"):
        account = reference[5:]
        username, separator, host = account.rpartition("@")
        if not separator or not username or not host or _is_private_host(host.lower()):
            raise ActorResolutionError("Remote acct handle is invalid")
        resource = urllib.parse.quote(f"acct:{username}@{host}", safe="@:")
        webfinger_url = f"https://{host}/.well-known/webfinger?resource={resource}"
        finger = _fetch_json(webfinger_url)
        actor_url_value = next(
            (link.get("href") for link in finger.get("links", [])
             if link.get("rel") == "self" and link.get("href")),
            None,
        )
        if not actor_url_value:
            raise ActorResolutionError("WebFinger did not return an actor")
        reference = str(actor_url_value)
    actor_url_value = _ensure_http_url(reference)
    return _validate_actor(_fetch_json(actor_url_value), actor_url_value)


def deliver_activity(inbox: str, activity: Mapping, actor: str) -> dict:
    """Deliver a signed activity and return a small transport result."""
    safe_inbox = _ensure_http_url(inbox)
    body = json.dumps(activity, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    headers = build_signed_headers("POST", safe_inbox, body, actor)
    headers.update({"Content-Type": ACTIVITY_CONTENT_TYPES.split(", ")[0], "Accept": ACTIVITY_CONTENT_TYPES, "User-Agent": FEDERATION_USER_AGENT})
    request = urllib.request.Request(safe_inbox, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=FEDERATION_FETCH_TIMEOUT_SECONDS) as response:
            status = int(response.getcode() or 200)
            response.read(4096)
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise DeliveryError("Remote federation inbox is unavailable") from exc
    if status < 200 or status >= 300:
        raise DeliveryError(f"Remote federation inbox rejected activity ({status})")
    return {"status": status}


def new_activity_id(actor: str) -> str:
    return f"{actor}/activities/{secrets.token_urlsafe(18)}"


def new_match_activity(actor: str, target: str) -> tuple[dict, str]:
    activity_id = new_activity_id(actor)
    match_id = f"{activity_id}#match"
    now = datetime.now(timezone.utc).isoformat()
    return (
        {
            "@context": ACTIVITYSTREAMS_CONTEXT,
            "id": activity_id,
            "type": "Create",
            "actor": actor,
            "to": [target],
            "object": {
                "id": match_id,
                "type": "KindredMatch",
                "actor": actor,
                "target": target,
                "published": now,
            },
        },
        match_id,
    )


def new_match_decision_activity(actor: str, target: str, match_id: str, accepted: bool) -> dict:
    return {
        "@context": ACTIVITYSTREAMS_CONTEXT,
        "id": new_activity_id(actor),
        "type": "Accept" if accepted else "Reject",
        "actor": actor,
        "to": [target],
        "object": match_id,
    }
