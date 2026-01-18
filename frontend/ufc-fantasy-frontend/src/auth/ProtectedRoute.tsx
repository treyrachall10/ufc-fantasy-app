import { useContext } from 'react';
import { Navigate, Outlet } from 'react-router-dom';
import { AuthContext } from '../auth/AuthProvider';

// Protects routes that require authentication.
// Redirects unauthenticated users to the sign-in page.
export default function ProtectedRoute() {
    const auth = useContext(AuthContext)!;

    if (!auth.token) {
        return <Navigate to="/sign-in" replace />;
    }
    return <Outlet />
}