import { createSlice, nanoid } from '@reduxjs/toolkit';

/**
 * chatSlice
 * ----------
 * Holds the AI Assistant conversation thread, plus loading/error UI state
 * for the current in-flight request to the backend /chat endpoint.
 */

const initialState = {
  messages: [
    // Seed assistant message shown on first load (matches reference UI placeholder).
    {
      id: 'seed-1',
      role: 'assistant',
      content:
        'Log interaction details here (e.g., "Met Dr. Smith, discussed Product X efficacy, positive sentiment, shared brochure") or ask for help.',
      createdAt: new Date().toISOString(),
      isSeed: true,
    },
  ],
  isLoading: false,
  error: null,
};

const chatSlice = createSlice({
  name: 'chat',
  initialState,
  reducers: {
    addUserMessage: {
      reducer: (state, action) => {
        state.messages.push(action.payload);
        state.error = null;
      },
      prepare: (content) => ({
        payload: {
          id: nanoid(),
          role: 'user',
          content,
          createdAt: new Date().toISOString(),
        },
      }),
    },
    addAssistantMessage: {
      reducer: (state, action) => {
        state.messages.push(action.payload);
      },
      prepare: (content) => ({
        payload: {
          id: nanoid(),
          role: 'assistant',
          content,
          createdAt: new Date().toISOString(),
        },
      }),
    },
    setLoading: (state, action) => {
      state.isLoading = action.payload;
    },
    setError: (state, action) => {
      state.error = action.payload;
      state.isLoading = false;
    },
    clearChat: () => initialState,
  },
});

export const { addUserMessage, addAssistantMessage, setLoading, setError, clearChat } =
  chatSlice.actions;

export const selectMessages = (state) => state.chat.messages;
export const selectChatLoading = (state) => state.chat.isLoading;
export const selectChatError = (state) => state.chat.error;

export default chatSlice.reducer;
