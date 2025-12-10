import { AppBar, Box, Container, Button, Avatar } from '@mui/material';
import Toolbar from '@mui/material/Toolbar';
import { deepOrange, orange } from '@mui/material/colors';
import { Link } from 'react-router-dom';

const pages = [{
        title: 'Dashboard',
        route: ''
                },
                {
        title: 'Fighters',
        route: '/fighters'
                },
                {
        title: 'Fights',
        route: '/fights'
                },
                {
        title: 'Events',
        route: '/events'         
                }]

export default function Navbar(){
    return (
        <AppBar position='static'>
            <Container maxWidth='xl'>
                <Toolbar disableGutters sx={{justifyContent: "space-between"}}>
                    <Box sx={{display: "flex"}}>
                        {pages.map((page) => (
                            <Link to={page.route} style={{textDecoration: "None"}}>
                                <Button
                                key={page.title}
                                variant="text"
                                sx={{ my: 2, color: 'white', display: 'block' }}
                                > {page.title}
                                </Button>
                            </Link>
                        ))}
                    </Box>
                        <Avatar sx={{bgcolor: deepOrange[500]}}>TR</Avatar>
                </Toolbar>
            </Container>
        </AppBar>
    )
}