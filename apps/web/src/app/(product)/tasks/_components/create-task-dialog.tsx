"use client";

import { useState } from "react";
import { useForm, Controller } from "react-hook-form";
import { standardSchemaResolver } from "@hookform/resolvers/standard-schema";
import { z } from "zod";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import type { WorkItem } from "@pinky/contracts";
import { api } from "@/lib/api";
import { QUERY_KEYS } from "@/lib/constants";
import { clustersOptions } from "../queries";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Plus } from "lucide-react";
import { toast } from "sonner";

const createTaskSchema = z.object({
  cluster_id: z.string().min(1, "Cluster is required"),
  title: z.string().min(1, "Title is required").max(200, "Title too long"),
  priority: z.enum(["low", "medium", "high", "critical"]),
  why_now: z.string().optional(),
  recommended_next_step: z.string().optional(),
});

type CreateTaskForm = z.infer<typeof createTaskSchema>;

export function CreateTaskDialog() {
  const [open, setOpen] = useState(false);
  const qc = useQueryClient();
  const { data: clusters } = useQuery(clustersOptions());

  const {
    register,
    handleSubmit,
    control,
    reset,
    formState: { errors },
  } = useForm<CreateTaskForm>({
    resolver: standardSchemaResolver(createTaskSchema),
    defaultValues: {
      priority: "medium",
      cluster_id: "",
      title: "",
      why_now: "",
      recommended_next_step: "",
    },
  });

  const create = useMutation({
    mutationFn: (data: CreateTaskForm) =>
      api.post<WorkItem>("/api/v1/work-items", {
        cluster_id: data.cluster_id,
        title: data.title,
        priority: data.priority,
        why_now: data.why_now || null,
        recommended_next_step: data.recommended_next_step || null,
        labels: {},
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: QUERY_KEYS.tasks() });
      reset();
      setOpen(false);
      toast.success("Task created");
    },
    onError: () => toast.error("Failed to create task"),
  });

  function onOpenChange(next: boolean) {
    setOpen(next);
    if (!next) reset();
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogTrigger asChild>
        <Button size="sm" className="gap-1">
          <Plus size={14} />
          New Task
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>New Task</DialogTitle>
          <DialogDescription>
            Create a standalone work item for your team.
          </DialogDescription>
        </DialogHeader>
        <form
          onSubmit={handleSubmit((data) => create.mutate(data))}
          className="space-y-4"
        >
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label className="text-xs text-text-secondary">
                Cluster <span className="text-destructive">*</span>
              </Label>
              <Controller
                name="cluster_id"
                control={control}
                render={({ field }) => (
                  <Select
                    value={field.value}
                    onValueChange={field.onChange}
                  >
                    <SelectTrigger
                      className="w-full"
                      aria-invalid={!!errors.cluster_id}
                    >
                      <SelectValue placeholder="Select cluster" />
                    </SelectTrigger>
                    <SelectContent>
                      {(clusters?.items ?? []).map((c) => (
                        <SelectItem key={c.id} value={c.id}>
                          {c.display_name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                )}
              />
              {errors.cluster_id && (
                <p className="text-caption text-destructive">
                  {errors.cluster_id.message}
                </p>
              )}
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs text-text-secondary">Priority</Label>
              <Controller
                name="priority"
                control={control}
                render={({ field }) => (
                  <Select
                    value={field.value}
                    onValueChange={field.onChange}
                  >
                    <SelectTrigger className="w-full">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="critical">Critical</SelectItem>
                      <SelectItem value="high">High</SelectItem>
                      <SelectItem value="medium">Medium</SelectItem>
                      <SelectItem value="low">Low</SelectItem>
                    </SelectContent>
                  </Select>
                )}
              />
            </div>
          </div>

          <div className="space-y-1.5">
            <Label className="text-xs text-text-secondary">
              Title <span className="text-destructive">*</span>
            </Label>
            <Input
              {...register("title")}
              placeholder="e.g. Scale frontend deployment to 5 replicas"
              aria-invalid={!!errors.title}
            />
            {errors.title && (
              <p className="text-caption text-destructive">
                {errors.title.message}
              </p>
            )}
          </div>

          <div className="space-y-1.5">
            <Label className="text-xs text-text-secondary">
              Situation context
            </Label>
            <Textarea
              {...register("why_now")}
              placeholder="Why does this need attention now?"
              rows={2}
            />
          </div>

          <div className="space-y-1.5">
            <Label className="text-xs text-text-secondary">
              Recommended next step
            </Label>
            <Textarea
              {...register("recommended_next_step")}
              placeholder="What should be done first?"
              rows={2}
            />
          </div>

          <DialogFooter>
            <Button
              type="submit"
              disabled={create.isPending}
              className="w-full"
            >
              {create.isPending ? "Creating..." : "Create Task"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
