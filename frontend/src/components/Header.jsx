import React from 'react';
import { Box, Typography } from '@mui/material';

const Header = () => {
  return (
    <Box sx={{ mb: 2 }}>
      <Typography variant="h5" component="h1" sx={{ color: 'text.primary' }}>
        Log HCP Interaction
      </Typography>
    </Box>
  );
};

export default Header;
