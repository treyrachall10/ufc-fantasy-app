import React from 'react';
import { useState } from 'react';
import logo from './logo.svg';
import './App.css';
import FightersListPage from './pages/FightersListPage'
import EventsListPage from './pages/EventsListPage'
import FightsListPage from './pages/FightsListPage';
import AthleteStatsPage from './pages/AthleteStatsPage';
import LeagueDashboard from './pages/LeagueDashboard';
import JoinLeague from './pages/JoinLeague';
import HomePage from './pages/Home';
import Navbar from './components/layout/Navbar';
import SignIn from './pages/SignIn';
import SignUp from './pages/SignUp';
import { Box, CssBaseline } from '@mui/material';
import UserTeamPage from './pages/UserTeamPage';
import DraftLobbyPage from './pages/DraftLobbyPage';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { AuthProvider } from './auth/AuthProvider';
import MainLayout from './components/layout/LayoutWithNavbar';
import AuthLayout from './components/layout/AuthLayout';
import {
  QueryClient,
  QueryClientProvider,
} from '@tanstack/react-query'
import { ReactQueryDevtools } from '@tanstack/react-query-devtools';
import '@mui/x-data-grid/themeAugmentation';
import ProtectedRoute from './auth/ProtectedRoute';
import LeaguesPage from './pages/LeaguesPage';
import LeagueCreation from './pages/LeagueCreation';

// Theme imports
import theme from './theme/theme';
import { ThemeProvider } from "@mui/material/styles";

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
                <Route path="/team/:teamId" element={<UserTeamPage />} />
                <Route path="/leagues" element={<LeaguesPage />} />
                <Route path="/join" element={<JoinLeague />} />
                <Route path="/draft" element={<DraftLobbyPage />} />
                <Route path="/leagues/create-league" element={<LeagueCreation />} />
                <Route element={<ProtectedRoute />}>
                  <Route path="/league/:leagueId" element={<LeagueDashboard />} />
                </Route>
              </Route>

              {/* Pages WITHOUT navbar */}
              <Route element={<AuthLayout />}>
                <Route path="/sign-in" element={<SignIn />} />
                <Route path="/sign-up" element={<SignUp />} />
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
