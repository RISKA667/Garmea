import { useState, useEffect } from 'react';

const useLocalStorage = (key, initialValue) => {
  // État pour stocker notre valeur
  // Passe une fonction à useState pour que la logique ne s'exécute qu'une seule fois
  const [storedValue, setStoredValue] = useState(() => {
    try {
      const item = window.localStorage.getItem(key);
      return item ? JSON.parse(item) : initialValue;
    } catch (error) {
      console.error(`Erreur lors de la lecture de la clé "${key}" du localStorage:`, error);
      return initialValue;
    }
  });

  // Fonction pour définir la valeur
  const setValue = (value) => {
    try {
      // Permet à la valeur d'être une fonction pour avoir la même API que useState
      const valueToStore = value instanceof Function ? value(storedValue) : value;
      setStoredValue(valueToStore);
      window.localStorage.setItem(key, JSON.stringify(valueToStore));
    } catch (error) {
      console.error(`Erreur lors de l'écriture de la clé "${key}" dans le localStorage:`, error);
    }
  };

  // Fonction pour supprimer la valeur
  const removeValue = () => {
    try {
      setStoredValue(initialValue);
      window.localStorage.removeItem(key);
    } catch (error) {
      console.error(`Erreur lors de la suppression de la clé "${key}" du localStorage:`, error);
    }
  };

  return [storedValue, setValue, removeValue];
};

export default useLocalStorage; 