export interface Principal {
  id: string;
  provider: string;
  subject: string;
  display_name: string | null;
  email: string | null;
  groups: string[];
  created_at: string;
  updated_at: string;
}
