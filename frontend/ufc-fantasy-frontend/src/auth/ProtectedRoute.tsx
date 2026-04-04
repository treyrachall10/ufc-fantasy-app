import { Navigate, Outlet } from 'react-router-dom';
import { useCurrentUser } from './useCurrentUser';
import { useAuth0 } from '@auth0/auth0-react';
import { Box, CircularProgress } from '@mui/material';

// Protects routes that require authentication.
// Redirects unauthenticated users to the sign-in page.
export default function ProtectedRoute() {
  const {isAuthenticated, isLoading} = useAuth0();
    const { data: user, isLoading: userLoading } = useCurrentUser()

    // Wait for Auth0 to finish loading before checking authentication
    if (isLoading || userLoading) {
        return (
            <Box display="flex" justifyContent="center" alignItems="center" minHeight="100vh">
                <CircularProgress />
            </Box>
        );
    }

    if (!isAuthenticated) {
        return <Navigate to="/sign-in" replace />;
    }
    
    if (user?.profile_complete === false) {
        return <Navigate to="/finish-signup" replace />;
    }
    
    return <Outlet />
}