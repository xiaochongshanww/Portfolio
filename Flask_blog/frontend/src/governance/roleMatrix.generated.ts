export const ROLE_MATRIX: Record<string,string[]> = {
  "articles:create": ["author","editor","admin"],
  "articles:update": ["author","editor","admin"],
  "articles:delete": ["editor","admin"],
  "workflow:submit": ["author","editor","admin"],
  "workflow:approve": ["editor","admin"],
  "workflow:reject": ["editor","admin"],
  "workflow:publish": ["editor","admin"],
  "comments:moderate": ["editor","admin"],
  "taxonomy:manage": ["editor","admin"],
  "users:change_role": ["admin"],
};
