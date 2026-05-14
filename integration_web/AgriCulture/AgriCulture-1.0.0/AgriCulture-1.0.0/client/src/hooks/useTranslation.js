import { useState, useCallback } from 'react';

const translations = {
  fr: {
    welcome: "Bienvenue sur AgriCulture",
    choose_role: "Choisissez votre rôle",
    farmer: "Agriculteur",
    researcher: "Chercheur",
    upload_image: "Télécharger une image",
    get_diagnosis: "Obtenir un diagnostic",
    recommendations: "Recommandations",
    login: "Connexion",
    signup: "S'inscrire",
    phone: "Numéro de téléphone",
    password: "Mot de passe",
    home: "Accueil",
    logout: "Déconnexion",
    back: "Retour",
    lang_toggle: "Derja (عربي)",
    portal: "Portail Agriculteur",
    welcome_sub: "Que souhaitez-vous faire aujourd'hui ?",
    action_sub: "Appuyez pour commencer",
  },
  derja: {
    welcome: "مرحباً بك في AgriCulture",
    choose_role: "اختار الدور متاعك",
    farmer: "فلاّح",
    researcher: "باحث",
    upload_image: "ابعث تصويرة",
    get_diagnosis: "شوف المرض",
    recommendations: "نصيحة",
    login: "دخول",
    signup: "سجل روحك",
    phone: "نومرو التليفون",
    password: "كلمة السر",
    home: "الواجهة",
    logout: "خروج",
    back: "رجوع",
    lang_toggle: "Français",
    portal: "بوابة الفلاح",
    welcome_sub: "شنية تحب تعمل اليوم؟",
    action_sub: "انزل باش تبدأ",
  }
};

export const useTranslation = (initialLang = 'fr') => {
  const [language, setLanguage] = useState(initialLang);

  const t = useCallback((key) => {
    return translations[language][key] || key;
  }, [language]);

  const toggleLanguage = () => {
    setLanguage(prev => prev === 'fr' ? 'derja' : 'fr');
  };

  return { t, language, setLanguage, toggleLanguage };
};
