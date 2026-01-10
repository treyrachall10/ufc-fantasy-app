import React from 'react';
import logo from './logo.svg';
import './App.css';
import FightersListPage from './pages/FightersListPage'
import EventsListPage from './pages/EventsListPage'
import FightsListPage from './pages/FightsListPage';
import AthleteStatsPage from './pages/AthleteStatsPage';
import HomePage from './pages/Home';
import Navbar from './components/layout/Navbar';
import { Container, CssBaseline } from '@mui/material';
import FightStatsPage from './pages/FightStatsPage';
import { BrowserRouter, Routes, Route} from 'react-router-dom';
import {
  useQuery,
  useMutation,
  useQueryClient,
  QueryClient,
  QueryClientProvider,
} from '@tanstack/react-query'
import { ReactQueryDevtools } from '@tanstack/react-query-devtools';
import { createTheme, ThemeProvider } from "@mui/material/styles";

declare module '@mui/material/styles' {
  interface TypographyVariants {
    body: React.CSSProperties;
    bodySmall: React.CSSProperties;
    kpiValue: React.CSSProperties;
    dataLabel: React.CSSProperties;
  }

  // allow configuration using `createTheme()`
  interface TypographyVariantsOptions {
    body?: React.CSSProperties;
    bodySmall?: React.CSSProperties;
    kpiValue?: React.CSSProperties;
    dataLabel?: React.CSSProperties;
  }

  // Custon color variants //
  interface Palette {
    brand: PaletteOptions['primary'];
    whiteAlpha20: PaletteOptions['primary'];
    dashboardBlack: PaletteOptions['primary'];
    brandAlpha50: PaletteOptions['primary'];
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
  }
}

// Update the Typography's variant prop options
declare module '@mui/material/Typography' {
  interface TypographyPropsVariantOverrides {
    body: true;
    bodySmall: true;
    kpiValue: true;
    dataLabel: true;
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
    //Need to load Inter
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
      fontWeight: 400,
      lineHeight: '1.3',
      letterSpacing: '-1em',
    },
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
    }
  }
})

function App() {
  const queryClient = new QueryClient();

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />

      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <Navbar />
          <Container maxWidth="xl" sx={{ display: 'flex', 
                                          flexDirection: 'column',
                                          justifyContent: 'center',
                                          alignItems: 'center',
                                          pt: '6rem',
                                          }}>
            <Routes>
              <Route path="/" element={<HomePage />} />
              <Route path="/fights" element={<FightsListPage />} />
              <Route path="/fights/:id" element={<FightsListPage />} />
              <Route path="/fighters" element={<FightersListPage />} />
              <Route path="/events" element={<EventsListPage />} />
              <Route path="/events/:id" element={<FightsListPage />} />
              <Route path="/fighter/:id" element={<AthleteStatsPage />} />
              <Route path="/fight/:id" element={<FightStatsPage />} />
            </Routes>
          </Container>
        </BrowserRouter>

        <ReactQueryDevtools initialIsOpen={false} />
      </QueryClientProvider>
    </ThemeProvider>
  );
}

export default App;
