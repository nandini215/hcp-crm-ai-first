import { createSlice } from '@reduxjs/toolkit';

/**
 * interactionSlice
 * ------------------
 * This slice is the SINGLE SOURCE OF TRUTH for the "Log HCP Interaction" form.
 *
 * IMPORTANT (by design):
 * The form fields are READ-ONLY in the UI. There are intentionally NO
 * field-level reducers (e.g. setHcpName, setDate, etc.). The only way this
 * state changes is via `setInteractionFromAI`, which is dispatched after the
 * backend AI agent (LangGraph + Groq) returns a structured JSON payload from
 * the /chat endpoint. This guarantees the form is always a mirror of AI output.
 */

export const initialInteractionState = {
  id: null,
  hcpName: '',
  interactionType: 'Meeting',
  date: '',
  time: '',
  attendees: '',
  topicsDiscussed: '',
  materialsShared: [], // array of strings, e.g. ["Product X Brochure"]
  samplesDistributed: [], // array of strings, e.g. ["OncoBoost 10mg x2"]
  sentiment: 'neutral', // 'positive' | 'neutral' | 'negative'
  outcomes: '',
  followUpActions: '',
  aiSuggestedFollowUps: [], // array of strings suggested by the AI assistant
  lastUpdated: null,
};

const interactionSlice = createSlice({
  name: 'interaction',
  initialState: initialInteractionState,
  reducers: {
    // The ONLY mutator for form data — always sourced from the AI response.
    setInteractionFromAI: (state, action) => {
      const payload = action.payload || {};
      return {
        ...state,
        ...payload,
        materialsShared: payload.materialsShared ?? state.materialsShared,
        samplesDistributed: payload.samplesDistributed ?? state.samplesDistributed,
        aiSuggestedFollowUps: payload.aiSuggestedFollowUps ?? state.aiSuggestedFollowUps,
        lastUpdated: new Date().toISOString(),
      };
    },
    // Appends an AI-suggested follow-up into the confirmed follow-up actions text.
    acceptSuggestedFollowUp: (state, action) => {
      const suggestion = action.payload;
      state.followUpActions = state.followUpActions
        ? `${state.followUpActions}\n- ${suggestion}`
        : `- ${suggestion}`;
      state.aiSuggestedFollowUps = state.aiSuggestedFollowUps.filter(
        (item) => item !== suggestion
      );
    },
    resetInteraction: () => initialInteractionState,
  },
});

export const { setInteractionFromAI, acceptSuggestedFollowUp, resetInteraction } =
  interactionSlice.actions;

// Selectors
export const selectInteraction = (state) => state.interaction;
export const selectHasInteractionData = (state) =>
  Boolean(state.interaction.hcpName || state.interaction.topicsDiscussed);

export default interactionSlice.reducer;
