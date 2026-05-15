"use client";

import { PageHeader } from "@/components/shared/page-header";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Server, FileText, Webhook, Shield, Users, BarChart3, Key, Wrench } from "lucide-react";
import { ClustersTab } from "./clusters-tab";
import { DefinitionsTab } from "./definitions-tab";
import { WebhooksTab } from "./webhooks-tab";
import { RulesTab } from "./rules-tab";
import { AccessTab } from "./access-tab";
import { AnalyticsTab } from "./analytics-tab";
import { TokensTab } from "./tokens-tab";
import { MaintenanceTab } from "./maintenance-tab";

export function SettingsView() {
  return (
    <div className="space-y-4">
      <PageHeader title="Settings" description="Platform configuration" />

      <Tabs defaultValue="clusters">
        <TabsList className="border-b border-border-default bg-transparent">
          <TabsTrigger value="clusters" className="gap-1.5"><Server size={14} />Clusters</TabsTrigger>
          <TabsTrigger value="definitions" className="gap-1.5"><FileText size={14} />Definitions</TabsTrigger>
          <TabsTrigger value="webhooks" className="gap-1.5"><Webhook size={14} />Webhooks</TabsTrigger>
          <TabsTrigger value="rules" className="gap-1.5"><Shield size={14} />Rules</TabsTrigger>
          <TabsTrigger value="access" className="gap-1.5"><Users size={14} />Access</TabsTrigger>
          <TabsTrigger value="analytics" className="gap-1.5"><BarChart3 size={14} />Analytics</TabsTrigger>
          <TabsTrigger value="tokens" className="gap-1.5"><Key size={14} />API Tokens</TabsTrigger>
          <TabsTrigger value="maintenance" className="gap-1.5"><Wrench size={14} />Maintenance</TabsTrigger>
        </TabsList>

        <TabsContent value="clusters"><ClustersTab /></TabsContent>
        <TabsContent value="definitions"><DefinitionsTab /></TabsContent>
        <TabsContent value="webhooks"><WebhooksTab /></TabsContent>
        <TabsContent value="rules"><RulesTab /></TabsContent>
        <TabsContent value="access"><AccessTab /></TabsContent>
        <TabsContent value="analytics"><AnalyticsTab /></TabsContent>
        <TabsContent value="tokens"><TokensTab /></TabsContent>
        <TabsContent value="maintenance"><MaintenanceTab /></TabsContent>
      </Tabs>
    </div>
  );
}
