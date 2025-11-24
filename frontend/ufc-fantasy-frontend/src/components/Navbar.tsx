import { AppBar, Box, Container, Button } from '@mui/material';
import Toolbar from '@mui/material/Toolbar';

const pages = ['Dashboard', 'Fighters', 'Fights', 'Events']
export default function Navbar(){
    return (
        <AppBar position='static'>
            <Container maxWidth='lg'>
                <Toolbar disableGutters>
                        {pages.map((page) => (
                            <Button
                            key={page}
                            variant="text"
                            sx={{ my: 2, color: 'white', display: 'block' }}
                            > {page}
                            </Button>
                        ))}
                </Toolbar>
            </Container>
        </AppBar>
    )
}