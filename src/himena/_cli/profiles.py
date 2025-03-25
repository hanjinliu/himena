from himena._cli.namespace import HimenaCliNamespace


def _assert_profile_not_none(profile: str | None) -> None:
    if profile is None:
        raise ValueError("Profile name is required with the --new option.")


def remove_profile(args: HimenaCliNamespace):
    _assert_profile_not_none(args.remove)
    args.assert_args_not_given()
    from himena.profile import remove_app_profile

    remove_app_profile(args.remove)
    print(f"Profile {args.remove!r} is removed.")


def new_profile(args: HimenaCliNamespace):
    _assert_profile_not_none(args.new)
    args.assert_args_not_given()
    from himena.profile import new_app_profile

    new_app_profile(args.new)
    print(
        f"Profile {args.new!r} is created. You can start the application with:\n"
        f"$ himena {args.new}"
    )
