import { useEffect, useState } from "react";
import { auth } from "@/app/lib/firebase-initialization"
import { IdTokenResult, User } from "firebase/auth";

export const emptyUser: User = {
  emailVerified: false,
  isAnonymous: false,
  metadata: {},
  providerData: [],
  refreshToken: "",
  tenantId: null,
  delete: function (): Promise<void> {
    throw new Error("Function not implemented.");
  },
  getIdToken: function (forceRefresh?: boolean | undefined): Promise<string> {
    throw new Error("Function not implemented.");
  },
  getIdTokenResult: function (forceRefresh?: boolean | undefined): Promise<IdTokenResult> {
    throw new Error("Function not implemented.");
  },
  reload: function (): Promise<void> {
    throw new Error("Function not implemented.");
  },
  toJSON: function (): object {
    throw new Error("Function not implemented.");
  },
  displayName: null,
  email: null,
  phoneNumber: null,
  photoURL: null,
  providerId: "",
  uid: ""
};

const useFirebaseAuthentication = () => {
  const [authUser, setAuthUser] = useState<User>(emptyUser);

  useEffect(() => {
    const unlisten = auth.onAuthStateChanged(
      authUser => {
        authUser
          ? setAuthUser(authUser)
          : setAuthUser(emptyUser);
      },
    );
    return () => {
      unlisten();
    }
  }, []);

  return authUser
}

export default useFirebaseAuthentication;