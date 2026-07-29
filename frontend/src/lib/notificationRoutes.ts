interface NotificationMeta {
  request_type?: string;
  request_id?: string;
}

/** Resolve in-app route for a notification click */
export function notificationRoute(
  notificationType: string,
  metadata?: NotificationMeta,
): string {
  const requestType = metadata?.request_type;

  if (notificationType === "approval_pending") {
    return "/app/approvals";
  }

  if (notificationType === "onboarding_assigned") {
    return "/app/profile";
  }

  if (notificationType === "approval_approved" || notificationType === "approval_rejected") {
    switch (requestType) {
      case "leave":
        return "/app/leave";
      case "wfh":
      case "regularization":
        return "/app/attendance";
      case "reimbursement":
        return "/app/finance";
      case "timesheet":
        return "/app/approvals";
      default:
        return "/app/approvals";
    }
  }

  return "/app/dashboard";
}
