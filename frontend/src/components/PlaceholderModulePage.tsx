import { Card, CardHeader } from "@/components/ui/Card";

export function PlaceholderModulePage({ title, description }: { title: string; description: string }) {
  return (
    <Card>
      <CardHeader title={title} description={description} />
      <p className="text-sm text-slate-500">Advanced features for this module coming in the next iteration.</p>
    </Card>
  );
}
