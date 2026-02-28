import { Outlet } from "react-router-dom";
import DashboardShell from "@/components/dashboard/DashboardShell";

export default function Dashboard() {
  return (
    <DashboardShell>
      <div className="flex-1 p-6 overflow-auto min-h-0">
        <Outlet />
      </div>
    </DashboardShell>
  );
}
