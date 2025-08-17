export const WORKFLOW_TRANSITIONS: Record<string,string[]> = {
  "draft": ["pending_review","archived"],
  "pending_review": ["rejected","published","archived"],
  "rejected": ["draft","pending_review","archived"],
  "scheduled": ["published","archived"],
  "published": ["archived"],
  "archived": [],
};
