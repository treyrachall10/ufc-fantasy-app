import { AppBar, 
            Box, 
            Container, 
            Button, 
            Typography, 
            IconButton,
            Menu,
            MenuItem,
        } from '@mui/material';
import * as React from 'react';
import MenuIcon from '@mui/icons-material/Menu';
import Toolbar from '@mui/material/Toolbar';
import { Link } from 'react-router-dom';
import fistLogo from '../../images/fist-svgrepo-com.svg';

const pages = [{
        title: 'Fighters',
        route: '/fighters'
                }, 
                {
        title: 'Leagues',
        route: '/fighters'
                }
        ]

export default function Navbar(){
    const [anchorElNav, setAnchorElNav] = React.useState<null | HTMLElement>(null);
    const [anchorElUser, setAnchorElUser] = React.useState<null | HTMLElement>(null);

    const handleOpenNavMenu = (event: React.MouseEvent<HTMLElement>) => {
        setAnchorElNav(event.currentTarget);
    };

    const handleCloseNavMenu = () => {
        setAnchorElNav(null);
    };

    return (
        <AppBar position='static' sx={{
                                    bgcolor: 'background.default', 
                                    }}>
            <Container maxWidth="xl">
                <Toolbar disableGutters>
                    <IconButton
                        component={Link}
                        to="/"
                        sx={{ display: { xs: 'none', md: 'flex' }, mr: 1 }}
                        >
                        <img
                            src={fistLogo}
                            alt="Home"
                            style={{ height: 32 }}
                        />
                    </IconButton>
                <Typography
                    variant="h6"
                    noWrap
                    component="a"
                    href="#app-bar-with-responsive-menu"
                    sx={{
                        mr: 2,
                        display: { xs: 'none', md: 'flex' },
                        fontFamily: 'monospace',
                        fontWeight: 700,
                        letterSpacing: '.3rem',
                        color: 'inherit',
                        textDecoration: 'none',
                    }}
                >
                    FantasyUFC
                </Typography>

                    <Box sx={{ flexGrow: 1, display: { xs: 'flex', md: 'none' } }}>
                        <IconButton
                        size="large"
                        aria-label="account of current user"
                        aria-controls="menu-appbar"
                        aria-haspopup="true"
                        onClick={handleOpenNavMenu}
                        color="inherit"
                        >
                        <MenuIcon />
                        </IconButton>
                        <Menu
                        id="menu-appbar"
                        anchorEl={anchorElNav}
                        anchorOrigin={{
                            vertical: 'bottom',
                            horizontal: 'left',
                        }}
                        keepMounted
                        transformOrigin={{
                            vertical: 'top',
                            horizontal: 'left',
                        }}
                        open={Boolean(anchorElNav)}
                        onClose={handleCloseNavMenu}
                        sx={{ display: { xs: 'block', md: 'none' } }}
                        >
                        {pages.map((page) => (
                            <MenuItem key={page.title} onClick={handleCloseNavMenu}>
                            <Typography sx={{ textAlign: 'center' }}>{page.title}</Typography>
                            </MenuItem>
                        ))}
                        </Menu>
                    </Box>
                    <IconButton
                        component={Link}
                        to="/"
                        sx={{ display: { xs: 'flex', md: 'none' }, mr: 1 }}
                        >
                        <img
                            src={fistLogo}
                            alt="Home"
                            style={{ height: 32 }}
                        />
                    </IconButton>
                    <Typography
                        variant="h5"
                        noWrap
                        component="a"
                        href="#app-bar-with-responsive-menu"
                        sx={{
                        mr: 2,
                        display: { xs: 'flex', md: 'none' },
                        flexGrow: 1,
                        fontFamily: 'monospace',
                        fontWeight: 700,
                        letterSpacing: '.3rem',
                        color: 'inherit',
                        textDecoration: 'none',
                        }}
                    >
                        FantasyUFC
                    </Typography>
                    <Box sx={{ flexGrow: 1, display: { xs: 'none', md: 'flex' } }}>
                        {pages.map((page) => (
                        <Button
                            key={page.title}
                            onClick={handleCloseNavMenu}
                            component={Link} to={page.route}
                            sx={{ my: 2, color: 'white', display: 'block', fontWeight: 400}}
                        >
                            {page.title}
                        </Button>
                        ))}
                    </Box>
                    <Box sx={{ display: 'flex', 
                        flexGrow: 0, gap: 1}}>
                        <Button variant='contained' color={"whiteAlpha20"}
                            sx={{borderColor: 'gray900.main',
                                '&:hover': {
                                borderColor: 'gray800.main'
                                    }
                                }}
                        >Sign In</Button>
                        <Button variant="contained" 
                                color='brandAlpha50' 
                                sx={{ 
                                        borderColor: 'brand.light',
                                        '&:hover': {
                                            borderColor: 'brand.main'
                                        }                        
                                    }}
                            >
                            Join a League
                        </Button>
                    </Box>
                </Toolbar>
            </Container>
        </AppBar>
    )
}