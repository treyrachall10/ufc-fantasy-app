import { Outlet } from 'react-router-dom';
import Navbar from './Navbar';
import { Box } from '@mui/material';

export default function MainLayout() {
  return (
    <>
      <Navbar />
      <Box sx={{pt: '6rem', alignItems: 'center'}}>
        <Outlet />
      </Box>
    </>
  );
}