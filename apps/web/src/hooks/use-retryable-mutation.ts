import {
  useMutation,
  type UseMutationOptions,
  type UseMutationResult,
} from "@tanstack/react-query";
import { toast } from "sonner";
import { SessionExpiredError, ClusterBindingError } from "@/lib/api";

interface RetryableMutationOptions<TData, TError, TVariables, TContext>
  extends UseMutationOptions<TData, TError, TVariables, TContext> {
  errorMessage: string;
}

export function useRetryableMutation<
  TData = unknown,
  TError = Error,
  TVariables = void,
  TContext = unknown,
>(
  options: RetryableMutationOptions<TData, TError, TVariables, TContext>,
): UseMutationResult<TData, TError, TVariables, TContext> {
  const { errorMessage, onError, ...rest } = options;

  const mutation = useMutation<TData, TError, TVariables, TContext>({
    ...rest,
    onError: (error, variables, context, mutation_instance) => {
      if (
        !(error instanceof SessionExpiredError) &&
        !(error instanceof ClusterBindingError)
      ) {
        toast.error(errorMessage, {
          action: {
            label: "Retry",
            onClick: () => mutation.mutate(variables),
          },
        });
      }
      onError?.(error, variables, context, mutation_instance);
    },
  });

  return mutation;
}
