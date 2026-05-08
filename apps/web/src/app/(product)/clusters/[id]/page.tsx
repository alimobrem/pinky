import { ClusterDetailView } from "./_components/cluster-detail-view";

export default function ClusterDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  return <ClusterDetailView paramsPromise={params} />;
}
