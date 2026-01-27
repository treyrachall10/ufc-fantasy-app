import { Outlet } from 'react-router-dom';
import Navbar from './Navbar';
import { Box } from '@mui/material';

export default function MainLayout() {
  return (
    <>
    <Box sx={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      <Navbar />
      <Box sx={{flex: 1, display: 'flex', justifyContent: 'center'}}>
        <Outlet />
      </Box>
      </Box>
    </>
  );
}