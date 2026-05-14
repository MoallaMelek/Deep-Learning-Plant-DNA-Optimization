export const speak = (text, lang = 'fr-FR') => {
  if (!window.speechSynthesis) return;

  // Cancel any ongoing speech
  window.speechSynthesis.cancel();

  const utterance = new SpeechSynthesisUtterance(text);
  
  // Set language. For Derja, we'll use Arabic (ar-SA or similar) if available, 
  // but most TTS engines don't have Derja specifically. 
  // We'll fallback to Arabic for Derja text.
  utterance.lang = lang === 'derja' ? 'ar-SA' : lang;
  
  utterance.rate = 0.9; // Slightly slower for better clarity
  utterance.pitch = 1;

  window.speechSynthesis.speak(utterance);
};
