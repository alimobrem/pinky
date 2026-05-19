import { describe, it, expect } from "vitest";
import {
  ApiError,
  SessionExpiredError,
  ClusterBindingError,
  ForbiddenError,
} from "./api";

describe("ApiError", () => {
  it("stores message and status", () => {
    const err = new ApiError("Not found", 404);
    expect(err.message).toBe("Not found");
    expect(err.status).toBe(404);
    expect(err.name).toBe("ApiError");
    expect(err).toBeInstanceOf(Error);
  });
});

describe("SessionExpiredError", () => {
  it("defaults to 401 with session message", () => {
    const err = new SessionExpiredError();
    expect(err.status).toBe(401);
    expect(err.message).toBe("Session expired");
    expect(err.name).toBe("SessionExpiredError");
    expect(err).toBeInstanceOf(ApiError);
  });

  it("accepts custom message", () => {
    const err = new SessionExpiredError("Token invalid");
    expect(err.message).toBe("Token invalid");
    expect(err.status).toBe(401);
  });
});

describe("ClusterBindingError", () => {
  it("sets 401 and custom message", () => {
    const err = new ClusterBindingError("Binding expired");
    expect(err.status).toBe(401);
    expect(err.message).toBe("Binding expired");
    expect(err.name).toBe("ClusterBindingError");
    expect(err).toBeInstanceOf(ApiError);
  });
});

describe("ForbiddenError", () => {
  it("sets 403 and message", () => {
    const err = new ForbiddenError("Access denied");
    expect(err.status).toBe(403);
    expect(err.message).toBe("Access denied");
    expect(err.name).toBe("ForbiddenError");
    expect(err).toBeInstanceOf(ApiError);
  });
});
