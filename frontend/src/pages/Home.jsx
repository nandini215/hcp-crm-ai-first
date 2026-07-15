import React from 'react';
import { Box, Grid } from '@mui/material';
import Header from '../components/Header';
import InteractionForm from '../components/InteractionForm';
import ChatPanel from '../components/ChatPanel';

/**
 * Home
 * -----
 * Top-level page: renders the page title plus the two-panel layout
 * (Interaction Details form on the left, AI Assistant chat on the right).
 */
const Home = () => {
  return (
    <Box sx={{ p: { xs: 2, md: 3 }, height: '100vh', display: 'flex', flexDirection: 'column' }}>
      <Header />
      <Grid container spacing={2} sx={{ flexGrow: 1, minHeight: 0 }}>
        <Grid item xs={12} md={8} sx={{ height: { md: '100%' } }}>
          <InteractionForm />
        </Grid>
        <Grid item xs={12} md={4} sx={{ height: { md: '100%' } }}>
          <ChatPanel />
        </Grid>
      </Grid>
    </Box>
  );
};

export default Home;
