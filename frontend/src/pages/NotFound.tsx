import { Compass } from "lucide-react";
import { Link } from "react-router";
import { Button, EmptyState } from "../components/ui";

export default function NotFound() {
  return (
    <EmptyState
      icon={<Compass className="size-10" />}
      title="Page not found"
      action={
        <Link to="/datasets">
          <Button variant="primary">Go to datasets</Button>
        </Link>
      }
    >
      The page you are looking for does not exist.
    </EmptyState>
  );
}
