import { Auth } from "firebase/auth";
import { useEffect, useState } from "react";

const useFirebaseAuthentication = (auth: Auth) => {
  const [authUser, setAuthUser] = useState(null);

  useEffect(() => {
    const unlisten = auth.onAuthStateChanged(
      authUser => {
        authUser
          ? setAuthUser(authUser)
          : setAuthUser(null);
      },
    );
    return () => {
      unlisten();
    }
  }, []);

  return authUser
}

export default useFirebaseAuthentication;