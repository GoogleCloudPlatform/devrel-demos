import { useState, useEffect, useRef } from "react";

export function useLocalStorage<T>(key: string, initialValue: T) {
  const [storedValue, setStoredValue] = useState<T>(initialValue);
  const [isLoaded, setIsLoaded] = useState(false);
  const isFirstRender = useRef(true);

  // Initial load
  useEffect(() => {
    if (typeof window === "undefined") return;
    try {
      const item = window.localStorage.getItem(key);
      if (item) {
        setStoredValue(JSON.parse(item));
      }
    } catch (error) {
      console.error("Error reading from localStorage", error);
    }
    setIsLoaded(true);
  }, [key]);

  // Use a functional update to ensure we always have the latest value
  // and sync to localStorage whenever storedValue changes (after initial load)
  const setValue = (value: T | ((val: T) => T)) => {
    setStoredValue((prev) => {
      const valueToStore = value instanceof Function ? value(prev) : value;
      try {
        if (typeof window !== "undefined") {
          window.localStorage.setItem(key, JSON.stringify(valueToStore));
        }
      } catch (e) {
        console.error("Error saving to localStorage", e);
      }
      return valueToStore;
    });
  };

  return [storedValue, setValue, isLoaded] as const;
}
