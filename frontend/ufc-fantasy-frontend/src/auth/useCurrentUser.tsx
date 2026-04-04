import { useQuery } from "@tanstack/react-query";
import { useAuthFetch } from './authFetch';
import { BackendUser } from '../types/types';

export const useCurrentUser = () => {
    const authFetch = useAuthFetch();
    return useQuery<BackendUser>({
        queryKey: ['me'],
        queryFn: () => authFetch(`http://localhost:8000/api/me`).then(r => r.json()),
        staleTime: 5 * 60 * 1000
    })
}