/**
 * caseMapper
 * -----------
 * The FastAPI backend returns interaction records with snake_case keys
 * (hcp_name, interaction_type, topics_discussed, ...) because that's the
 * natural convention for the Python/SQLAlchemy models. The Redux store and
 * every component in this app (interactionSlice, InteractionForm) expect
 * camelCase keys (hcpName, interactionType, topicsDiscussed, ...).
 *
 * This is the single boundary where that translation happens — every place
 * that receives a raw API interaction payload should pass it through
 * `mapInteractionFromApi` before it reaches Redux.
 */

const toCamel = (key) => key.replace(/_([a-z0-9])/g, (_, c) => c.toUpperCase());

export const mapInteractionFromApi = (interaction) => {
  if (!interaction || typeof interaction !== 'object') return interaction;

  const mapped = {};
  Object.entries(interaction).forEach(([key, value]) => {
    mapped[toCamel(key)] = value;
  });

  // Normalize "HH:MM:SS" (Pydantic's default time serialization) down to
  // "HH:MM" so it matches the value format <input type="time"> expects.
  if (typeof mapped.time === 'string' && mapped.time.length > 5) {
    mapped.time = mapped.time.slice(0, 5);
  }

  return mapped;
};

export default { mapInteractionFromApi };
