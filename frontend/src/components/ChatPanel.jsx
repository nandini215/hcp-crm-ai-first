import React, { useEffect, useRef, useState } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import {
  Paper,
  Box,
  Typography,
  TextField,
  Button,
  Stack,
  Avatar,
  CircularProgress,
  Alert,
} from '@mui/material';
import SmartToyOutlinedIcon from '@mui/icons-material/SmartToyOutlined';
import PersonOutlineIcon from '@mui/icons-material/PersonOutline';
import WarningAmberIcon from '@mui/icons-material/WarningAmber';
import SendIcon from '@mui/icons-material/Send';
import { sendChatMessage } from '../services/chatService';
import {
  addUserMessage,
  addAssistantMessage,
  setLoading,
  setError,
  selectMessages,
  selectChatLoading,
  selectChatError,
} from '../redux/chatSlice';
import { setInteractionFromAI, selectInteraction } from '../redux/interactionSlice';

/**
 * ChatPanel
 * ----------
 * The right-hand "AI Assistant" panel. The user describes an HCP
 * interaction in natural language. On submit ("Log"), the message is:
 *   1. Pushed into the chat thread (Redux: chatSlice)
 *   2. POSTed to /chat (FastAPI -> LangGraph agent -> Groq gemma2-9b-it)
 *   3. The structured JSON response updates interactionSlice, which
 *      automatically re-renders the read-only InteractionForm.
 */
const ChatPanel = () => {
  const dispatch = useDispatch();
  const messages = useSelector(selectMessages);
  const isLoading = useSelector(selectChatLoading);
  const error = useSelector(selectChatError);
  const interaction = useSelector(selectInteraction);

  const [input, setInput] = useState('');
  const scrollRef = useRef(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, isLoading]);

  const handleLog = async () => {
    const trimmed = input.trim();
    if (!trimmed || isLoading) return;

    dispatch(addUserMessage(trimmed));
    setInput('');
    dispatch(setLoading(true));

    try {
      const data = await sendChatMessage(trimmed, interaction.id);
      // Expected response shape:
      // { reply: string, interaction: { hcpName, interactionType, date, ... } }
      if (data?.interaction) {
        dispatch(setInteractionFromAI(data.interaction));
      }
      dispatch(addAssistantMessage(data?.reply || 'Interaction logged and form updated.'));
    } catch (err) {
      dispatch(setError(err.message));
      dispatch(
        addAssistantMessage(
          "I couldn't reach the server just now. Please check the backend connection and try again."
        )
      );
    } finally {
      dispatch(setLoading(false));
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleLog();
    }
  };

  return (
    <Paper variant="outlined" sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      {/* Header */}
      <Box sx={{ p: 2, borderBottom: '1px solid', borderColor: 'divider' }}>
        <Stack direction="row" spacing={1} alignItems="center">
          <SmartToyOutlinedIcon fontSize="small" color="primary" />
          <Typography variant="subtitle2" sx={{ fontSize: '0.95rem' }}>
            AI Assistant
          </Typography>
        </Stack>
        <Typography variant="caption" sx={{ color: 'text.secondary', ml: 3.5 }}>
          Log interaction via chat
        </Typography>
      </Box>

      {/* Conversation */}
      <Box
        ref={scrollRef}
        sx={{
          flexGrow: 1,
          overflowY: 'auto',
          p: 2,
          display: 'flex',
          flexDirection: 'column',
          gap: 1.5,
          bgcolor: '#fbfbfc',
        }}
      >
        {messages.map((msg) => (
          <MessageBubble key={msg.id} message={msg} />
        ))}

        {isLoading && (
          <Stack direction="row" spacing={1} alignItems="center" sx={{ pl: 1 }}>
            <CircularProgress size={16} />
            <Typography variant="caption" color="text.secondary">
              AI Assistant is analyzing your note...
            </Typography>
          </Stack>
        )}

        {error && (
          <Alert severity="error" icon={<WarningAmberIcon fontSize="small" />} sx={{ fontSize: '0.8rem' }}>
            {error}
          </Alert>
        )}
      </Box>

      {/* Input + Log button */}
      <Box sx={{ p: 1.5, borderTop: '1px solid', borderColor: 'divider' }}>
        <Stack direction="row" spacing={1}>
          <TextField
            fullWidth
            multiline
            maxRows={4}
            placeholder="Describe interaction..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={isLoading}
          />
          <Button
            variant="contained"
            color="inherit"
            onClick={handleLog}
            disabled={isLoading || !input.trim()}
            startIcon={<SendIcon fontSize="small" />}
            sx={{
              bgcolor: '#374151',
              color: '#fff',
              '&:hover': { bgcolor: '#1f2937' },
              whiteSpace: 'nowrap',
              px: 2.5,
            }}
          >
            Log
          </Button>
        </Stack>
      </Box>
    </Paper>
  );
};

const MessageBubble = ({ message }) => {
  const isUser = message.role === 'user';
  return (
    <Stack
      direction="row"
      spacing={1}
      alignItems="flex-start"
      sx={{ flexDirection: isUser ? 'row-reverse' : 'row' }}
    >
      <Avatar
        sx={{
          width: 28,
          height: 28,
          bgcolor: isUser ? 'primary.main' : '#e5e7eb',
          color: isUser ? '#fff' : '#374151',
        }}
      >
        {isUser ? <PersonOutlineIcon fontSize="small" /> : <SmartToyOutlinedIcon fontSize="small" />}
      </Avatar>
      <Box
        sx={{
          maxWidth: '80%',
          bgcolor: isUser ? 'primary.main' : '#eef2f7',
          color: isUser ? '#fff' : 'text.primary',
          px: 1.5,
          py: 1,
          borderRadius: 2,
          borderTopRightRadius: isUser ? 4 : 16,
          borderTopLeftRadius: isUser ? 16 : 4,
        }}
      >
        <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap' }}>
          {message.content}
        </Typography>
      </Box>
    </Stack>
  );
};

export default ChatPanel;
