import { Conversation, Message } from "../types";

// Quick prompt suggestions
export const QUICK_PROMPTS = [
  "Tell me about Mondstadt",
  "Best team compositions",
  "Explain elemental reactions",
];

// Generate a unique ID
export function generateId(): string {
  return Math.random().toString(36).substring(2, 15) + Date.now().toString(36);
}

// Placeholder recent conversations
export function getPlaceholderConversations(): Conversation[] {
  const now = new Date();
  return [
    {
      id: generateId(),
      sessionId: generateId(),
      title: "About Primogems and wi...",
      messages: [],
      createdAt: new Date(now.getTime() - 30 * 60 * 1000), // 30 min ago
      updatedAt: new Date(now.getTime() - 30 * 60 * 1000),
    },
    {
      id: generateId(),
      sessionId: generateId(),
      title: "Best team compositions",
      messages: [],
      createdAt: new Date(now.getTime() - 2 * 60 * 60 * 1000), // 2 hours ago
      updatedAt: new Date(now.getTime() - 2 * 60 * 60 * 1000),
    },
    {
      id: generateId(),
      sessionId: generateId(),
      title: "Lore discussion: Archons",
      messages: [],
      createdAt: new Date(now.getTime() - 24 * 60 * 60 * 1000), // 1 day ago
      updatedAt: new Date(now.getTime() - 24 * 60 * 60 * 1000),
    },
    {
      id: generateId(),
      sessionId: generateId(),
      title: "Elemental reactions guide",
      messages: [],
      createdAt: new Date(now.getTime() - 2 * 24 * 60 * 60 * 1000), // 2 days ago
      updatedAt: new Date(now.getTime() - 2 * 24 * 60 * 60 * 1000),
    },
    {
      id: generateId(),
      sessionId: generateId(),
      title: "Exploration tips for Sume...",
      messages: [],
      createdAt: new Date(now.getTime() - 3 * 24 * 60 * 60 * 1000), // 3 days ago
      updatedAt: new Date(now.getTime() - 3 * 24 * 60 * 60 * 1000),
    },
    {
      id: generateId(),
      sessionId: generateId(),
      title: "Character builds: Nahida",
      messages: [],
      createdAt: new Date(now.getTime() - 5 * 24 * 60 * 60 * 1000), // 5 days ago
      updatedAt: new Date(now.getTime() - 5 * 24 * 60 * 60 * 1000),
    },
  ];
}

// Placeholder assistant responses based on keywords
const KEYWORD_RESPONSES: Record<string, string> = {
  mondstadt: "Mondstadt, the City of Freedom, is one of the seven nations of Teyvat. It sits on a vast lake in the northeastern part of Teyvat and is governed by the Knights of Favonius. The Anemo Archon Barbatos watches over this city, though he prefers to stay hands-off with its governance. The city is known for its wine, particularly the famous Dandelion Wine produced by the Dawn Winery.",
  liyue: "Liyue Harbor is the largest and most prosperous commercial port in Teyvat. Located in the eastern part of the continent, it's ruled by the Geo Archon, Rex Lapis (also known as Morax or Zhongli). The nation is known for its rich mineral resources, ancient traditions, and the Qixing - seven business leaders who handle the city's affairs.",
  inazuma: "Inazuma is an isolated island nation in the east of Teyvat, ruled by the Electro Archon, the Raiden Shogun. The nation was locked in the Vision Hunt Decree, where the Shogun confiscated Visions in pursuit of eternity. The nation consists of six main islands and is known for its Japanese-inspired culture and the Grand Narukami Shrine.",
  sumeru: "Sumeru is the nation of wisdom, ruled by the Dendro Archon, Lesser Lord Kusanali (Nahida). It's home to the Akademiya, the most prestigious academic institution in Teyvat. The nation is divided into the rainforest and the desert regions, each with distinct cultures and challenges.",
  team: "For strong team compositions, consider these archetypes:\n\n1. **National Team**: Xiangling, Bennett, Xingqiu + flex (great for elemental reactions)\n2. **Freeze Team**: Ayaka/Ganyu + Mona/Kokomi + Anemo + Cryo battery\n3. **Taser Team**: Fischl + Beidou + Xingqiu + Sucrose\n4. **Hyperbloom**: Nahida + Raiden + Xingqiu + flex\n\nThe best team depends on the content and your available characters!",
  elemental: "Elemental reactions are the core of Genshin Impact's combat system:\n\n**Amplifying Reactions:**\n- Melt (Pyro + Cryo): 2x or 1.5x damage\n- Vaporize (Pyro + Hydro): 2x or 1.5x damage\n\n**Transformative Reactions:**\n- Overloaded (Pyro + Electro): AoE Pyro damage\n- Superconduct (Cryo + Electro): Reduces physical resistance\n- Electro-Charged (Hydro + Electro): Continuous damage\n- Swirl (Anemo + element): Spreads and amplifies elements\n\n**Dendro Reactions:**\n- Bloom, Hyperbloom, Burgeon, Quicken, Aggravate, Spread",
  primogem: "Primogems are the premium currency in Genshin Impact. Here are ways to obtain them:\n\n- Daily Commissions: 60 primogems/day\n- Spiral Abyss: Up to 600 primogems twice per month\n- Events: Variable amounts\n- Exploration: Chests and achievements\n- Quests: Story and world quests\n- Maintenance compensation: 300+ primogems\n\n160 primogems = 1 Intertwined Fate (wish)",
  archon: "The Seven Archons are the divine rulers of the seven nations of Teyvat:\n\n1. **Barbatos** (Venti) - Anemo Archon of Mondstadt\n2. **Morax** (Zhongli) - Geo Archon of Liyue\n3. **Raiden Ei** - Electro Archon of Inazuma\n4. **Nahida** - Dendro Archon of Sumeru\n5. **Focalors** - Hydro Archon of Fontaine\n6. **Murata** - Pyro Archon of Natlan\n7. **Tsaritsa** - Cryo Archon of Snezhnaya",
};

const FALLBACK_RESPONSES = [
  "That's an interesting question about Teyvat! While I search my knowledge, feel free to ask about specific regions, characters, team compositions, or game mechanics.",
  "Hmm, let me think about that... In the meantime, is there something specific about Genshin Impact you'd like to know? I can help with lore, gameplay tips, or character builds!",
  "Great question, Traveler! I'd be happy to help you explore the world of Teyvat. Could you tell me more about what aspect you're curious about?",
  "The world of Genshin Impact is vast and full of secrets! I'm here to help guide you through Teyvat. What would you like to learn more about?",
  "As your companion through Teyvat, I'm always ready to assist! Whether it's about the seven nations, elemental reactions, or character strategies - just ask!",
];

export function generatePlaceholderResponse(userMessage: string): string {
  const lowerMessage = userMessage.toLowerCase();
  
  // Check for keyword matches
  for (const [keyword, response] of Object.entries(KEYWORD_RESPONSES)) {
    if (lowerMessage.includes(keyword)) {
      return response;
    }
  }
  
  // Return a random fallback response
  const randomIndex = Math.floor(Math.random() * FALLBACK_RESPONSES.length);
  return FALLBACK_RESPONSES[randomIndex];
}

// Create a new empty conversation
export function createNewConversation(): Conversation {
  const now = new Date();
  return {
    id: generateId(),
    sessionId: generateId(),
    title: "New Conversation",
    messages: [],
    createdAt: now,
    updatedAt: now,
  };
}

// Create a message
export function createMessage(role: "user" | "assistant", content: string): Message {
  return {
    id: generateId(),
    role,
    content,
    createdAt: new Date(),
  };
}

// Derive title from first user message
export function deriveTitleFromMessage(message: string): string {
  const maxLength = 25;
  const cleaned = message.trim();
  if (cleaned.length <= maxLength) {
    return cleaned;
  }
  return cleaned.substring(0, maxLength) + "...";
}
