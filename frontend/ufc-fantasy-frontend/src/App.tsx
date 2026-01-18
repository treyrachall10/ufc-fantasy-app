import React from 'react';
import { useState } from 'react';
import logo from './logo.svg';
import './App.css';
import FightersListPage from './pages/FightersListPage'
import EventsListPage from './pages/EventsListPage'
import FightsListPage from './pages/FightsListPage';
import AthleteStatsPage from './pages/AthleteStatsPage';
import LeagueDashboard from './pages/LeagueDashboard';
import HomePage from './pages/Home';
import Navbar from './components/layout/Navbar';
import SignIn from './pages/SignIn';
import SignUp from './pages/SignUp';
import { Box, CssBaseline } from '@mui/material';
import FightStatsPage from './pages/FightStatsPage';
import UserTeamPage from './pages/UserTeamPage';
import { BrowserRouter, Routes, Route} from 'react-router-dom';
import { AuthProvider } from './auth/AuthProvider';
import MainLayout from './components/layout/LayoutWithNavbar';
import AuthLayout from './components/layout/AuthLayout';
import {
  QueryClient,
  QueryClientProvider,
} from '@tanstack/react-query'
import { ReactQueryDevtools } from '@tanstack/react-query-devtools';
import { createTheme, ThemeProvider } from "@mui/material/styles";
import '@mui/x-data-grid/themeAugmentation';
import { getToken } from './auth/auth';
import ProtectedRoute from './auth/ProtectedRoute';

declare module '@mui/material/styles' {
  interface TypographyVariants {
    body: React.CSSProperties;
    bodySmall: React.CSSProperties;
    kpiValue: React.CSSProperties;
    dataLabel: React.CSSProperties;
    metaText: React.CSSProperties;
    metaLabel: React.CSSProperties;
  }

  // allow configuration using `createTheme()`
  interface TypographyVariantsOptions {
    body?: React.CSSProperties;
    bodySmall?: React.CSSProperties;
    kpiValue?: React.CSSProperties;
    dataLabel?: React.CSSProperties;
    metaText?: React.CSSProperties;
    metaLabel?: React.CSSProperties;
  }

  // Custon color variants //
  interface Palette {
    brand: PaletteOptions['primary'];
    whiteAlpha20: PaletteOptions['primary'];
    dashboardBlack: PaletteOptions['primary'];
    brandAlpha50: PaletteOptions['primary'];
    brandAlpha75: PaletteOptions['primary'];
    gray800?: PaletteOptions['primary'];
    gray900?: PaletteOptions['primary'];
  }

  interface PaletteOptions {
    brand?: PaletteOptions['primary'];
    whiteAlpha20?: PaletteOptions['primary'];
    dashboardBlack?: PaletteOptions['primary'];
    brandAlpha50?: PaletteOptions['primary'];
    gray800?: PaletteOptions['primary'];
    gray900?: PaletteOptions['primary'];
    brandAlpha75?: PaletteOptions['primary'];
  }
}

// Update the Typography's variant prop options
declare module '@mui/material/Typography' {
  interface TypographyPropsVariantOverrides {
    body: true;
    bodySmall: true;
    kpiValue: true;
    dataLabel: true;
    metaText: true;
    metaLabel: true;
  }
}

// Update the breakpoint prop options
declare module '@mui/material/styles' {
  interface BreakpointOverrides {
    // Custom Breakpoints
    laptop: true;
    tablet: true;
    mobile: true;
    desktop: true;
    // Remove default breakpoints
  }
}

declare module '@mui/material/Button' {
  interface ButtonPropsColorOverrides {
    brand: true;
    dashboardBlack: true;
    brandAlpha50: true;
    whiteAlpha20: true;
  }
}

declare module '@mui/material/AppBar' {
  interface AppBarPropsColorOverrides {
    brand: true;
  }
}

const theme = createTheme({
  typography: {
    fontFamily: '"Inter", "Roboto"',
    fontSize: 16,
    body1: undefined,
    h1: { // Hero Title
      fontSize: "4rem",
      lineHeight: "3.8rem",
      letterSpacing: "-.02em",
      fontWeight: 600,
    },
    h2: { // Page Titles
      fontSize: "1.95rem",
      lineHeight: "1.1rem",
      letterSpacing: "-.02em",
      fontWeight: 600,
    },
    h3: { // Secondary Sections
      fontSize: "1.5rem",
      lineHeight: "1.3rem",
      letterSpacing: "-.02em",
      fontWeight: 600,
    },
    subtitle1: { // Under Titles
      fontSize: "1.5rem",
      lineHeight: "1.4rem",
      letterSpacing: '-0.01em',
      fontWeight: 500,
    },
    subtitle2: { // Card titles, Chart titles, Hover Card titles (UI label)
      fontSize: '1rem',
      lineHeight: '1.3rem',
      letterSpacing: '0.01em',
      fontWeight: 500,
    },
    body: { // Paragraphs, Descriptons, Explanations (Long text)
      fontSize: '1rem',
      fontWeight: 400,
      lineHeight: '1.6',
      letterSpacing: '0.03em',
    },
    bodySmall: { // list contents
      fontSize: '.95rem',
      fontWeight: 400,
      lineHeight: '1.65',
      letterSpacing: '0.03em',
    },
    dataLabel: { // X/Y axis labels
      fontSize: '.95rem',
      fontWeight: 300,
      lineHeight: '1.65',
      letterSpacing: '0.03em',
    },
    caption: { // KPI labels
      fontSize: '.85rem',
      fontWeight: 400,
      lineHeight: '1.65',
      letterSpacing: '0.03em',
    },
    button: {
      fontSize: '1rem',
      fontWeight: 500,
      lineHeight: '1.6',
      letterSpacing: '0.03em',
    },
    kpiValue: {
      fontSize: '3rem',
      fontWeight: 300,
      lineHeight: '1.3',
      letterSpacing: '-0.03em',
    },
    metaText: {
      fontSize: "1.5rem",
      lineHeight: "1.3rem",
      letterSpacing: "-.02em",
      fontWeight: 400,
    },
    metaLabel: {
      fontSize: "1.5rem",
      lineHeight: "1.3rem",
      letterSpacing: "-.02em",
      fontWeight: 300,
    }
  },
  palette: {
      brand: { // Defines the main brand color
        main: 'hsla(0, 91%, 43%, 1)',    // 100%
        light: 'hsla(0, 91%, 43%, 0.3)', // 30%
        dark: 'hsla(0, 91%, 43%, 0.05)', // 5%
      },
      brandAlpha50: { // Defines the brand color 50% alpha channel
        main: 'hsla(0, 91%, 43%, 0.5)',
      },
      brandAlpha75: { // Defines the brand color 75% alpha channel
        main: 'hsla(0, 91%, 43%, 0.75)',
      },
      background: { // Defines the defualt background color
        default: 'hsla(135, 8%, 10%, 1)'
      },
      text: { // Defines the text default color
        primary: 'hsl(0, 0%, 100%)',
        secondary: 'hsla(0, 0%, 100%, 0.50)',
      },
      whiteAlpha20: {
        main: 'hsla(0, 0%, 21%, 0.20)'
      },
      dashboardBlack: { // Dashbpoard component backgrounds
        main: 'hsla(150, 8%, 5%, 1)'
      },
      gray800: { // Lighter gray for hover border on off buttons
        main: 'hsla(0, 0%, 27%, 1)'
      },
      gray900: { // Darker gray for standard border on off buttons
        main: 'hsla(0, 0%, 21%, 1)'
      },
  },
  components: {
    MuiCssBaseline: {
    styleOverrides: {
      body: {
        
        minHeight: '100vh',
      },
    },
  },
    MuiButton: {
      styleOverrides: {
        root: {
          borderRadius: '.5rem',
          textTransform: 'none',
          color: 'white',
        },
        contained: {
          border: '1px solid',
        }
      }
    },
    MuiDataGrid: {
      styleOverrides: {
        root: {
          border: 0,
          borderRadius: 8,
          //Makes borders invisible (if they were instead removed sizing would mess up)
          "--DataGrid-rowBorderColor": "transparent",
          "--DataGrid-borderColor": "transparent",
          "--DataGrid-columnSeparatorColor": "transparent",
          "& .MuiDataGrid-columnSeparator": { opacity: 0 },
          //Colors
          "& .MuiDataGrid-columnHeader": {backgroundColor:  'hsla(150, 8%, 5%, 1)'},
          backgroundColor: 'hsla(150, 8%, 5%, 1)',
          "& .MuiDataGrid-columnHeaderTitle":{
            color: 'hsla(0, 0%, 100%, 0.50)',
            fontWeight: '300',
          },
        }
      }
    },
    MuiOutlinedInput: {
      styleOverrides: {
        notchedOutline: {
          borderColor: 'hsla(0, 0%, 21%, 1)',
        },
        root: {
          '&:hover .MuiOutlinedInput-notchedOutline': {
            borderColor: 'hsla(0, 0%, 27%, 1)',
          },
          '&.Mui-focused .MuiOutlinedInput-notchedOutline': {
            borderColor: 'hsla(0, 0%, 21%, 1)',
          },
          '&.Mui-error .MuiOutlinedInput-notchedOutline': {
            borderColor: 'error.main',
          },
        },
      },
    },
    MuiInputBase: {
      styleOverrides: {
        input: {
          backgroundColor: 'rgba(5, 7, 10, 0.5)',
          borderRadius: 6,
        }
      }
    },
    MuiMenuItem: {
      styleOverrides: {
        root: {
          backgroundColor: 'hsla(135, 8%, 10%, 1)'
        }
      }
    },
    MuiList: {
      styleOverrides: {
        root: {
          backgroundColor: 'hsla(135, 8%, 10%, 1)'
        }
      }
    },
    MuiPaper: {
      styleOverrides: {
        root: {
          backgroundColor: 'hsla(135, 8%, 10%, 1)'
        }
      }
    }
  },
  breakpoints: {
    values: {
    xs: 0,
    sm: 600,
    md: 900,
    lg: 1200,
    xl: 1536,
    mobile: 475,
    tablet: 800,
    laptop: 1200,
    desktop: 1440,
    },
  },
})

function App() {
const queryClient = new QueryClient();

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />

        <QueryClientProvider client={queryClient}>
          <AuthProvider>
          <BrowserRouter>
            <Routes>

              {/* Pages WITH navbar */}
              <Route element={<MainLayout />}>
                <Route path="/" element={<HomePage />} />
                <Route path="/fights" element={<FightsListPage />} />
                <Route path="/fights/:id" element={<FightsListPage />} />
                <Route path="/fighters" element={<FightersListPage />} />
                <Route path="/events" element={<EventsListPage />} />
                <Route path="/events/:id" element={<FightsListPage />} />
                <Route path="/fighter/:id" element={<AthleteStatsPage />} />
                <Route path="/fight/:id" element={<FightStatsPage />} />
                <Route path="/fighter" element={<AthleteStatsPage />} />
                <Route path="/team" element={<UserTeamPage />} />
                <Route element={<ProtectedRoute/>}>
                  <Route path="/league" element={<LeagueDashboard />} />
                </Route>
              </Route>

              {/* Pages WITHOUT navbar */}
              <Route element={<AuthLayout />}>
                <Route path="/sign-in" element={<SignIn/>} />
                <Route path="/sign-up" element={<SignUp/>} />
              </Route>

            </Routes>
          </BrowserRouter>
          </AuthProvider>
          <ReactQueryDevtools initialIsOpen={false} />
        </QueryClientProvider>

    </ThemeProvider>
  );
}

export default App;
