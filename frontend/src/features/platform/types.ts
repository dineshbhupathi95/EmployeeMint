export interface TenantAdmin {
  user_id: string;
  employee_id: string | null;
  email: string;
  first_name: string | null;
  last_name: string | null;
  is_active: boolean;
  last_login_at: string | null;
  role_name: string;
}

export interface TenantDetail {
  id: string;
  name: string;
  slug: string;
  custom_domain: string | null;
  plan: string;
  max_employees: number;
  is_active: boolean;
  is_setup_complete: boolean;
  enabled_modules: Record<string, boolean>;
  created_at: string;
  updated_at: string;
  employee_count: number;
  admins: TenantAdmin[];
}

export interface TenantSummary {
  id: string;
  name: string;
  slug: string;
  plan: string;
  max_employees: number;
  is_active: boolean;
  is_setup_complete: boolean;
}

export interface PaginatedTenants {
  items: TenantSummary[];
  total: number;
  page: number;
  page_size: number;
}
