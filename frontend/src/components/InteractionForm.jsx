import React from 'react';
import { useDispatch, useSelector } from 'react-redux';
import {
  Box,
  Paper,
  Typography,
  Grid,
  TextField,
  MenuItem,
  Button,
  Divider,
  Radio,
  RadioGroup,
  FormControlLabel,
  Chip,
  Stack,
  List,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Tooltip,
} from '@mui/material';
import SearchIcon from '@mui/icons-material/Search';
import AddCircleOutlineIcon from '@mui/icons-material/AddCircleOutline';
import MicNoneIcon from '@mui/icons-material/MicNone';
import AutoAwesomeIcon from '@mui/icons-material/AutoAwesome';
import SentimentSatisfiedAltIcon from '@mui/icons-material/SentimentSatisfiedAlt';
import SentimentNeutralIcon from '@mui/icons-material/SentimentNeutral';
import SentimentDissatisfiedIcon from '@mui/icons-material/SentimentDissatisfied';
import AddIcon from '@mui/icons-material/Add';
import {
  selectInteraction,
  acceptSuggestedFollowUp,
} from '../redux/interactionSlice';

const INTERACTION_TYPES = ['Meeting', 'Call', 'Email', 'Conference', 'Virtual Visit'];

/**
 * InteractionForm
 * -----------------
 * Renders the "Interaction Details" panel as a strictly READ-ONLY view of
 * Redux `interaction` state. No field here accepts manual text entry —
 * every value shown is the result of the AI Assistant's structured output
 * from the /chat endpoint (see ChatPanel.jsx + redux/interactionSlice.js).
 */
const InteractionForm = () => {
  const dispatch = useDispatch();
  const interaction = useSelector(selectInteraction);

  const {
    hcpName,
    interactionType,
    date,
    time,
    attendees,
    topicsDiscussed,
    materialsShared,
    samplesDistributed,
    sentiment,
    outcomes,
    followUpActions,
    aiSuggestedFollowUps,
  } = interaction;

  const handleAcceptSuggestion = (suggestion) => {
    dispatch(acceptSuggestedFollowUp(suggestion));
  };

  return (
    <Paper variant="outlined" sx={{ p: 3, height: '100%', overflowY: 'auto' }}>
      <Typography variant="subtitle2" sx={{ fontSize: '1rem', mb: 2.5 }}>
        Interaction Details
      </Typography>

      <Grid container spacing={2.5}>
        {/* HCP Name / Interaction Type */}
        <Grid item xs={12} sm={6}>
          <FieldLabel>HCP Name</FieldLabel>
          <TextField
            fullWidth
            placeholder="Search or select HCP..."
            value={hcpName}
            InputProps={{ readOnly: true }}
            disabled
          />
        </Grid>
        <Grid item xs={12} sm={6}>
          <FieldLabel>Interaction Type</FieldLabel>
          <TextField
            select
            fullWidth
            value={interactionType || 'Meeting'}
            InputProps={{ readOnly: true }}
            disabled
          >
            {INTERACTION_TYPES.map((type) => (
              <MenuItem key={type} value={type}>
                {type}
              </MenuItem>
            ))}
          </TextField>
        </Grid>

        {/* Date / Time */}
        <Grid item xs={12} sm={6}>
          <FieldLabel>Date</FieldLabel>
          <TextField
            fullWidth
            type="date"
            value={date || ''}
            InputProps={{ readOnly: true }}
            disabled
          />
        </Grid>
        <Grid item xs={12} sm={6}>
          <FieldLabel>Time</FieldLabel>
          <TextField
            fullWidth
            type="time"
            value={time || ''}
            InputProps={{ readOnly: true }}
            disabled
          />
        </Grid>

        {/* Attendees */}
        <Grid item xs={12}>
          <FieldLabel>Attendees</FieldLabel>
          <TextField
            fullWidth
            placeholder="Enter names or search..."
            value={attendees}
            InputProps={{ readOnly: true }}
            disabled
          />
        </Grid>

        {/* Topics Discussed */}
        <Grid item xs={12}>
          <FieldLabel>Topics Discussed</FieldLabel>
          <TextField
            fullWidth
            multiline
            minRows={3}
            placeholder="Enter key discussion points..."
            value={topicsDiscussed}
            InputProps={{
              readOnly: true,
              endAdornment: (
                <MicNoneIcon fontSize="small" sx={{ color: 'text.disabled', alignSelf: 'flex-end' }} />
              ),
            }}
            disabled
          />
          <Tooltip title="Voice-note summarization is handled by the AI Assistant chat">
            <span>
              <Button
                size="small"
                startIcon={<AutoAwesomeIcon fontSize="small" />}
                disabled
                sx={{ mt: 1, color: 'text.secondary', bgcolor: '#f3f4f6' }}
              >
                Summarize from Voice Note (Requires Consent)
              </Button>
            </span>
          </Tooltip>
        </Grid>

        {/* Materials / Samples */}
        <Grid item xs={12}>
          <Typography variant="subtitle2" sx={{ mb: 1.5 }}>
            Materials Shared / Samples Distributed
          </Typography>

          <MaterialsBlock
            title="Materials Shared"
            items={materialsShared}
            emptyLabel="No materials added."
            actionLabel="Search/Add"
            actionIcon={<SearchIcon fontSize="small" />}
          />

          <Divider sx={{ my: 2 }} />

          <MaterialsBlock
            title="Samples Distributed"
            items={samplesDistributed}
            emptyLabel="No samples added."
            actionLabel="Add Sample"
            actionIcon={<AddCircleOutlineIcon fontSize="small" />}
          />
        </Grid>

        {/* Sentiment */}
        <Grid item xs={12}>
          <FieldLabel>Observed/Inferred HCP Sentiment</FieldLabel>
          <RadioGroup row value={sentiment || 'neutral'} sx={{ mt: 0.5 }}>
            <FormControlLabel
              value="positive"
              control={<Radio disabled icon={<SentimentSatisfiedAltIconMuted />} checkedIcon={<SentimentSatisfiedAltIcon color="success" />} />}
              label="Positive"
              disabled
            />
            <FormControlLabel
              value="neutral"
              control={<Radio disabled icon={<SentimentNeutralIconMuted />} checkedIcon={<SentimentNeutralIcon color="warning" />} />}
              label="Neutral"
              disabled
            />
            <FormControlLabel
              value="negative"
              control={<Radio disabled icon={<SentimentDissatisfiedIconMuted />} checkedIcon={<SentimentDissatisfiedIcon color="error" />} />}
              label="Negative"
              disabled
            />
          </RadioGroup>
        </Grid>

        {/* Outcomes */}
        <Grid item xs={12}>
          <FieldLabel>Outcomes</FieldLabel>
          <TextField
            fullWidth
            multiline
            minRows={2}
            placeholder="Key outcomes or agreements..."
            value={outcomes}
            InputProps={{ readOnly: true }}
            disabled
          />
        </Grid>

        {/* Follow-up Actions */}
        <Grid item xs={12}>
          <FieldLabel>Follow-up Actions</FieldLabel>
          <TextField
            fullWidth
            multiline
            minRows={2}
            placeholder="Enter next steps or tasks..."
            value={followUpActions}
            InputProps={{ readOnly: true }}
            disabled
          />

          {aiSuggestedFollowUps?.length > 0 && (
            <Box sx={{ mt: 1.5 }}>
              <Typography variant="caption" sx={{ display: 'block', fontWeight: 600, color: 'text.secondary', mb: 0.5 }}>
                AI Suggested Follow-ups:
              </Typography>
              <List dense disablePadding>
                {aiSuggestedFollowUps.map((suggestion) => (
                  <ListItemButton
                    key={suggestion}
                    onClick={() => handleAcceptSuggestion(suggestion)}
                    sx={{ py: 0.25, px: 0.5, borderRadius: 1 }}
                  >
                    <ListItemIcon sx={{ minWidth: 24 }}>
                      <AddIcon fontSize="small" color="primary" />
                    </ListItemIcon>
                    <ListItemText
                      primaryTypographyProps={{ variant: 'body2', color: 'primary' }}
                      primary={suggestion}
                    />
                  </ListItemButton>
                ))}
              </List>
            </Box>
          )}
        </Grid>
      </Grid>
    </Paper>
  );
};

/* ---------- Small presentational helpers ---------- */

const FieldLabel = ({ children }) => (
  <Typography variant="body2" sx={{ fontWeight: 600, mb: 0.5, color: 'text.primary' }}>
    {children}
  </Typography>
);

const MaterialsBlock = ({ title, items, emptyLabel, actionLabel, actionIcon }) => (
  <Box>
    <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 0.75 }}>
      <Typography variant="body2" sx={{ fontWeight: 600 }}>
        {title}
      </Typography>
      <Tooltip title="Managed automatically by the AI Assistant">
        <span>
          <Button size="small" variant="outlined" startIcon={actionIcon} disabled>
            {actionLabel}
          </Button>
        </span>
      </Tooltip>
    </Stack>
    {items && items.length > 0 ? (
      <Stack direction="row" flexWrap="wrap" gap={1}>
        {items.map((item) => (
          <Chip key={item} label={item} size="small" sx={{ bgcolor: '#eef2ff' }} />
        ))}
      </Stack>
    ) : (
      <Typography variant="caption" sx={{ fontStyle: 'italic', color: 'text.disabled' }}>
        {emptyLabel}
      </Typography>
    )}
  </Box>
);

/* Muted (unchecked) sentiment icons so the radio row matches the reference UI */
const SentimentSatisfiedAltIconMuted = () => (
  <SentimentSatisfiedAltIcon fontSize="small" sx={{ color: '#d1d5db' }} />
);
const SentimentNeutralIconMuted = () => (
  <SentimentNeutralIcon fontSize="small" sx={{ color: '#d1d5db' }} />
);
const SentimentDissatisfiedIconMuted = () => (
  <SentimentDissatisfiedIcon fontSize="small" sx={{ color: '#d1d5db' }} />
);

export default InteractionForm;
