import React from 'react';
import logo from './logo.svg';
import './App.css';
import FightersListPage from './pages/FightersListPage'
import EventsListPage from './pages/EventsListPage'
import FightsListPage from './pages/FightsListPage';
import AthleteStatsPage from './pages/AthleteStatsPage';
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

function App() {
  
  const queryClient = new QueryClient()

  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <CssBaseline/>
          <Navbar/>
          <Container maxWidth='xl' sx={{py: 3}}>
              <Routes>
                <Route path="/fights" element={<FightsListPage/>} />
                <Route path="/fights/:id" element={<FightsListPage/>} />
                <Route path="/fighters" element={<FightersListPage/>} />
                <Route path="/events" element={<EventsListPage/>} />
                <Route path="/events/:id" element={<FightsListPage/>}/>
                <Route path="/fighter/:id" element={<AthleteStatsPage/>} />
                <Route path="/fight/:id" element={<FightStatsPage/>} />
            </Routes> 
          </Container>
      </BrowserRouter>
      <ReactQueryDevtools initialIsOpen={false} />
  </QueryClientProvider>
  );
}

export default App;
