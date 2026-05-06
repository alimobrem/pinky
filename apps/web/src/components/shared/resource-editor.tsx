"use client";

import { useState, useCallback } from "react";
import Editor from "@monaco-editor/react";
import { useMutation } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { Badge } from "@/components/ui/badge";
import { FileCode, Download, Upload, RotateCcw, Loader2 } from "lucide-react";
import { toast } from "sonner";

interface ResourceEditorProps {
  clusterId: string;
  namespace: string;
  kind: string;
  name: string;
}

export function ResourceEditor({ clusterId, namespace, kind, name }: ResourceEditorProps) {
  const [yaml, setYaml] = useState<string>("");
  const [originalYaml, setOriginalYaml] = useState<string>("");
  const [loaded, setLoaded] = useState(false);

  const fetch = useMutation({
    mutationFn: () =>
      api.get<{ yaml: string }>(
        `/api/v1/clusters/${clusterId}/resources/${namespace}/${kind}/${name}`,
      ),
    onSuccess: (data) => {
      setYaml(data.yaml);
      setOriginalYaml(data.yaml);
      setLoaded(true);
    },
    onError: () => toast.error("Failed to fetch resource"),
  });

  const apply = useMutation({
    mutationFn: () =>
      api.put<{ yaml: string }>(
        `/api/v1/clusters/${clusterId}/resources/${namespace}/${kind}/${name}`,
        { yaml_content: yaml },
      ),
    onSuccess: (data) => {
      setYaml(data.yaml);
      setOriginalYaml(data.yaml);
      toast.success("Resource applied");
    },
    onError: () => toast.error("Failed to apply resource"),
  });

  const hasChanges = yaml !== originalYaml;

  const handleReset = useCallback(() => {
    setYaml(originalYaml);
  }, [originalYaml]);

  if (!loaded) {
    return (
      <Card>
        <CardContent className="flex items-center justify-center py-8">
          <Button
            variant="outline"
            className="gap-2"
            onClick={() => fetch.mutate()}
            disabled={fetch.isPending}
          >
            {fetch.isPending ? (
              <Loader2 size={14} className="animate-spin" />
            ) : (
              <Download size={14} />
            )}
            Load {kind}/{name}
          </Button>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="flex items-center justify-between">
          <span className="flex items-center gap-2 text-caption font-semibold uppercase tracking-widest text-text-tertiary">
            <FileCode size={14} className="text-brand-purple" />
            Resource Editor
          </span>
          <div className="flex items-center gap-2">
            <Badge variant="outline" className="font-mono text-caption">
              {kind}/{namespace}/{name}
            </Badge>
            {hasChanges && (
              <Badge className="bg-status-in-progress/20 text-status-in-progress">
                Modified
              </Badge>
            )}
          </div>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="overflow-hidden rounded-lg border border-border-subtle">
          <Editor
            height="400px"
            language="yaml"
            theme="vs-dark"
            value={yaml}
            onChange={(v) => setYaml(v ?? "")}
            options={{
              minimap: { enabled: false },
              fontSize: 12,
              lineNumbers: "on",
              scrollBeyondLastLine: false,
              wordWrap: "on",
              tabSize: 2,
              readOnly: apply.isPending,
            }}
          />
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            className="gap-2"
            onClick={() => fetch.mutate()}
            disabled={fetch.isPending}
          >
            <Download size={14} />
            Refresh
          </Button>

          <Button
            variant="outline"
            size="sm"
            className="gap-2"
            onClick={handleReset}
            disabled={!hasChanges}
          >
            <RotateCcw size={14} />
            Reset
          </Button>

          <div className="flex-1" />

          <AlertDialog>
            <AlertDialogTrigger asChild>
              <Button
                size="sm"
                className="gap-2"
                disabled={!hasChanges || apply.isPending}
              >
                {apply.isPending ? (
                  <Loader2 size={14} className="animate-spin" />
                ) : (
                  <Upload size={14} />
                )}
                Apply
              </Button>
            </AlertDialogTrigger>
            <AlertDialogContent>
              <AlertDialogHeader>
                <AlertDialogTitle>Apply changes to {kind}/{name}?</AlertDialogTitle>
                <AlertDialogDescription>
                  This will patch {kind} &quot;{name}&quot; in namespace &quot;{namespace}&quot;
                  on the cluster. This action is logged and auditable.
                </AlertDialogDescription>
              </AlertDialogHeader>
              <AlertDialogFooter>
                <AlertDialogCancel>Cancel</AlertDialogCancel>
                <AlertDialogAction
                  className="bg-brand-pink text-text-inverse hover:bg-brand-pink-dim"
                  onClick={() => apply.mutate()}
                >
                  Apply
                </AlertDialogAction>
              </AlertDialogFooter>
            </AlertDialogContent>
          </AlertDialog>
        </div>
      </CardContent>
    </Card>
  );
}
