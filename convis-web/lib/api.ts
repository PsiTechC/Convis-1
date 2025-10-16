// API Configuration
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export interface RegisterData {
  companyName: string;
  email: string;
  password: string;
  phoneNumber: string;
}

export interface RegisterResponse {
  message: string;
  userId?: string;
}

export interface VerifyEmailData {
  email: string;
  otp: string;
}

export interface VerifyEmailResponse {
  message: string;
}

export interface ApiError {
  detail: string;
}

export async function registerUser(data: RegisterData): Promise<RegisterResponse> {
  const response = await fetch(`${API_BASE_URL}/api/register/`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(data),
  });

  const result = await response.json();

  if (!response.ok) {
    throw new Error(result.detail || 'Registration failed');
  }

  return result;
}

export async function verifyEmail(data: VerifyEmailData): Promise<VerifyEmailResponse> {
  const response = await fetch(`${API_BASE_URL}/api/register/verify-email`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(data),
  });

  const result = await response.json();

  if (!response.ok) {
    throw new Error(result.detail || 'Verification failed');
  }

  return result;
}

export interface LoginData {
  email: string;
  password: string;
}

export interface LoginResponse {
  redirectUrl: string;
  clientId: string;
  isAdmin_683ed29d13d9992915a2a803_amdin_: boolean;
  token: string;
}

export async function loginUser(data: LoginData): Promise<LoginResponse> {
  const response = await fetch(`${API_BASE_URL}/api/access/login`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(data),
  });

  const result = await response.json();

  if (!response.ok) {
    throw new Error(result.detail || 'Login failed');
  }

  return result;
}
