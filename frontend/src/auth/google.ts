declare global {
  interface Window {
    google?: any;
  }
}

export function getGoogleClientId(): string {
  throw new Error("Google login is disabled");
}

export async function renderGoogleButton(container: HTMLDivElement, onIdToken: (idToken: string) => void) {
  void container;
  void onIdToken;
  throw new Error("Google login is disabled");
}

export function cancelGooglePrompt() {
  // no-op (Google login disabled)
}
