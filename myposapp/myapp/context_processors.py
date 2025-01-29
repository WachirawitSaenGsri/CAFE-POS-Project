def user_store_info(request):
    if request.user.is_authenticated:
        user = request.user
        member_profile = user.member_profile
        store = member_profile.store
        store_name = store.name
        return {
            'user_first_name': user.first_name,
            'user_last_name': user.last_name,
            'user_role': member_profile.role,  # Access role from member_profile
            'store_name': store_name,
        }
    return {}