import { useQuery } from "@tanstack/react-query";
import { useAuthFetch } from './authFetch';
import { useAuth0, User } from '@auth0/auth0-react';

export const useCurrentUser = () => {
    const authFetch = useAuthFetch();
    return useQuery<User>({
        queryKey: ['me'],
        queryFn: () => authFetch(`http://localhost:8000/api/me`).then(r => r.json()),
        staleTime: 5 * 60 * 1000
    })
}