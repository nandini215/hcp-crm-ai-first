import axiosInstance from './axiosInstance';
import { mapInteractionFromApi } from '../utils/caseMapper';

/**
 * sendChatMessage
 * -----------------
 * Sends the user's natural-language interaction note to the FastAPI backend.
 * The backend runs it through the LangGraph agent (Groq tool-calling ->
 * log_interaction/edit_interaction/etc. -> PostgreSQL write), and returns:
 * {
 *   reply: string,                       // assistant's natural-language reply
 *   interaction: { hcp_name, ... }        // snake_case, straight from FastAPI
 * }
 *
 * We translate `interaction` to camelCase here (see utils/caseMapper.js) so
 * every consumer downstream (interactionSlice, InteractionForm) can work with
 * a single consistent shape.
 */
export const sendChatMessage = async (message, currentInteractionId = null) => {
  const response = await axiosInstance.post('/chat', {
    message,
    interaction_id: currentInteractionId,
  });

  const data = response.data || {};
  return {
    reply: data.reply,
    interaction: mapInteractionFromApi(data.interaction),
  };
};

export default { sendChatMessage };
