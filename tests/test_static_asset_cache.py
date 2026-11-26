from static_asset_cache import cache_control_for_asset


def test_versioned_public_assets_are_immutable():
    assert cache_control_for_asset("/public/nimi-theme.css", versioned=True) == (
        "public, max-age=31536000, immutable"
    )


def test_unversioned_public_assets_get_short_cache():
    assert cache_control_for_asset("/public/nimi-logo.svg") == "public, max-age=300"


def test_hashed_chainlit_bundle_is_immutable():
    assert cache_control_for_asset("/assets/index-a1b2c3d4e5.js") == (
        "public, max-age=31536000, immutable"
    )


def test_unhashed_bundle_is_not_immutable():
    assert cache_control_for_asset("/assets/index.js") is None


def test_private_and_api_routes_are_never_cached_by_this_policy():
    for path in (
        "/guest-auth",
        "/api/threads",
        "/project/threads",
        "/private-storage/guest/file.pdf",
        "/healthz",
        "/readyz",
    ):
        assert cache_control_for_asset(path, versioned=True) is None
