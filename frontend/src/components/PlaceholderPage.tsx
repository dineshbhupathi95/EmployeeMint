import { Card, CardHeader } from "@/components/ui/Card";

export function PlaceholderPage({ title, description }: { title: string; description: string }) {
  return (
    <Card>
      <CardHeader title={title} description={description} />
      <p className="text-sm text-slate-500">This module will be built in the next phase.</p>
    </Card>
  );
}
