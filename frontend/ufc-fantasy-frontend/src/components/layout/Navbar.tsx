import { AppBar, 
            Box, 
            Button, 
            Typography, 
            IconButton,
            Menu,
            MenuItem,
        } from '@mui/material';
import { Avatar } from '@mui/material';
import * as React from 'react';
import MenuIcon from '@mui/icons-material/Menu';
import Toolbar from '@mui/material/Toolbar';
import { Link } from 'react-router-dom';
import fistLogo from '../../images/fist-svgrepo-com.svg';
import { useContext } from 'react';
import { AuthContext } from '../../auth/AuthProvider';
import { useNavigate } from 'react-router-dom';

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
    const navigate = useNavigate();
    // Gives access to token state directly
    const auth = useContext(AuthContext)!;

    const [anchorElNav, setAnchorElNav] = React.useState<null | HTMLElement>(null);
    const [anchorElUser, setAnchorElUser] = React.useState<null | HTMLElement>(null);

    const handleOpenNavMenu = (event: React.MouseEvent<HTMLElement>) => {
        setAnchorElNav(event.currentTarget);
    };

    const handleCloseNavMenu = () => {
        setAnchorElNav(null);
    };

    const handleOpenUserMenu = (event: React.MouseEvent<HTMLElement>) => {
        setAnchorElUser(event.currentTarget);
    }

    const handleCloseUserMenu = () => {
        setAnchorElUser(null);
    }

    const settings = [
        { label: 'Profile', to: '/profile' },
        { label: 'Account', to: '/account' },
        { label: 'Dashboard', to: '/league' },
        {
            label: 'Logout',
            action: () => {
            auth.logout();
            navigate('/sign-in');
            },
        },
    ];

    return (
        <AppBar position='static' sx={{
                                    bgcolor: 'background.default',
                                    px: '16px'
                                    }}>
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
                            <MenuItem 
                                key={page.title} 
                                onClick={handleCloseNavMenu}
                                sx={{
                                    '&:hover': {
                                        backgroundColor: 'rgba(255, 255, 255, 0.04)'
                                    }
                                }}
                                >
                                <Typography 
                                    sx={{ 
                                        textAlign: 'center' 
                                    }}
                                    >
                                        {page.title}
                                    </Typography>
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
                    <Box 
                        sx={{ 
                            display: 'flex', 
                            flexGrow: 0, 
                            gap: 1
                            }}
                        >
                            {/* render sign in button if user not logged in*/}
                            {!auth.token && (
                                <Button 
                                    variant='contained' 
                                    color={"whiteAlpha20"}
                                    component={Link} to="/sign-in"
                                    sx={{
                                        textWrap: 'nowrap',
                                        borderColor: 'gray900.main',
                                        '&:hover': {
                                        borderColor: 'gray800.main'
                                            }
                                    }}
                                >
                                    Sign In
                                </Button>
                                )}
                        <Button 
                            variant="contained" 
                            color='brandAlpha50' 
                            sx={{
                                display: {xs: 'none', md:'flex'},
                                borderColor: 'brand.light',
                                '&:hover': {
                                    borderColor: 'brand.main'
                                }                        
                                }}
                        >
                            Join a League
                        </Button>
                        {auth.token && (
                            <>
                                <IconButton
                                    onClick={handleOpenUserMenu}
                                >
                                    <Avatar alt="Profile Picture"/>
                                </IconButton>
                                <Menu
                                    anchorEl={anchorElUser}
                                    open={Boolean(anchorElUser)}
                                    onClose={handleCloseUserMenu}
                                >
                                    {settings.map((setting) => (
                                        <MenuItem key={setting.label} onClick={() => {
                                            setting.action?.(); // Will only run if setting.action exist in list
                                            handleCloseUserMenu();
                                        }}>
                                            <Typography sx={{ textAlign: 'center' }}>{setting.label}</Typography>
                                        </MenuItem>
                                    ))}
                                </Menu>
                            </>
                        )}
                    </Box>
                </Toolbar>
        </AppBar>
    )
}