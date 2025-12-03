import { AppBar, Box, Container, Button, Avatar } from '@mui/material';
import Toolbar from '@mui/material/Toolbar';
import { deepOrange, orange } from '@mui/material/colors';

const pages = ['Dashboard', 'Fighters', 'Fights', 'Events']

export default function Navbar(){
    return (
        <AppBar position='static'>
            <Container maxWidth='xl'>
                <Toolbar disableGutters sx={{justifyContent: "space-between"}}>
                    <Box sx={{display: "flex"}}>
                        {pages.map((page) => (
                            <Button
                            key={page}
                            variant="text"
                            sx={{ my: 2, color: 'white', display: 'block' }}
                            > {page}
                            </Button>
                        ))}
                    </Box>
                        <Avatar sx={{bgcolor: deepOrange[500]}}>TR</Avatar>
                </Toolbar>
            </Container>
        </AppBar>
    )
}