import { http } from "@/lib/http";

export const zone1 = {
  live: () => http<any>("/api/zone1/live"),
};
