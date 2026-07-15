import { configureStore } from '@reduxjs/toolkit';
import interactionReducer from '../redux/interactionSlice';
import chatReducer from '../redux/chatSlice';

export const store = configureStore({
  reducer: {
    interaction: interactionReducer,
    chat: chatReducer,
  },
  devTools: import.meta.env.DEV,
});

export default store;
