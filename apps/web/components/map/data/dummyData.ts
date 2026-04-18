export type VolunteerPin = {
  id: string; name: string; lat: number; lng: number;
  status: "available" | "busy"; skills: string[]; initials: string;
  assignedTo?: string;
};

export type OperationPin = {
  id: string; title: string; lat: number; lng: number;
  status: "critical" | "active" | "completed";
  assigned: number; needed: number; description: string;
};

export type ResourcePin = {
  id: string; title: string; lat: number; lng: number;
  type: "medical" | "food" | "equipment"; stock: number;
};

export const VOLUNTEERS: VolunteerPin[] = [
  { id: "v1",  name: "Priya Sharma",  lat: 28.6139, lng: 77.2090, status: "available", skills: ["Medical", "Teaching"],       initials: "PS", assignedTo: "op1" },
  { id: "v2",  name: "Rahul Gupta",   lat: 19.0760, lng: 72.8777, status: "available", skills: ["Logistics", "Driving"],      initials: "RG", assignedTo: "op2" },
  { id: "v3",  name: "Ananya Singh",  lat: 12.9716, lng: 77.5946, status: "busy",      skills: ["IT Support", "Teaching"],    initials: "AS" },
  { id: "v4",  name: "Vikram Patel",  lat: 23.0225, lng: 72.5714, status: "available", skills: ["Medical", "First Aid"],      initials: "VP" },
  { id: "v5",  name: "Kavya Reddy",   lat: 17.3850, lng: 78.4867, status: "available", skills: ["Finance", "Admin"],          initials: "KR" },
  { id: "v6",  name: "Arjun Mehta",   lat: 22.5726, lng: 88.3639, status: "available", skills: ["Construction", "Logistics"], initials: "AM" },
  { id: "v7",  name: "Divya Nair",    lat: 13.0827, lng: 80.2707, status: "busy",      skills: ["Teaching", "Child Care"],    initials: "DN", assignedTo: "op2" },
  { id: "v8",  name: "Suresh Kumar",  lat: 26.8467, lng: 80.9462, status: "available", skills: ["Driving", "Logistics"],      initials: "SK", assignedTo: "op1" },
  { id: "v9",  name: "Meera Joshi",   lat: 21.1458, lng: 79.0882, status: "available", skills: ["Medical", "Nursing"],        initials: "MJ" },
  { id: "v10", name: "Aditya Verma",  lat: 30.7333, lng: 76.7794, status: "busy",      skills: ["Admin", "Finance"],          initials: "AV" },
];

export const OPERATIONS: OperationPin[] = [
  { id: "op1", title: "Flood Relief — Lucknow", lat: 26.8467, lng: 80.9462, status: "critical",  assigned: 3, needed: 8,  description: "Immediate evacuation and medical aid for flood-affected families." },
  { id: "op2", title: "Food Drive — Mumbai",    lat: 19.1136, lng: 72.8697, status: "active",    assigned: 5, needed: 5,  description: "Weekly food distribution at 12 collection points across Mumbai." },
  { id: "op3", title: "Medical Camp — Jaipur",  lat: 26.9124, lng: 75.7873, status: "active",    assigned: 2, needed: 4,  description: "Free health checkups and medicine for rural communities." },
  { id: "op4", title: "Education Drive — Pune", lat: 18.5204, lng: 73.8567, status: "completed", assigned: 6, needed: 6,  description: "School supply distribution completed successfully." },
  { id: "op5", title: "Drought Relief — Nashik",lat: 20.0059, lng: 73.7879, status: "critical",  assigned: 1, needed: 10, description: "Emergency water and food supplies urgently required." },
];

export const RESOURCES: ResourcePin[] = [
  { id: "r1", title: "Medical Depot — Delhi",      lat: 28.7041, lng: 77.1025, type: "medical",   stock: 450 },
  { id: "r2", title: "Food Storage — Navi Mumbai", lat: 19.0330, lng: 73.0297, type: "food",      stock: 200 },
  { id: "r3", title: "Equipment Hub — Bangalore",  lat: 12.8969, lng: 77.5905, type: "equipment", stock: 80  },
  { id: "r4", title: "Medical Cache — Hyderabad",  lat: 17.4065, lng: 78.4772, type: "medical",   stock: 310 },
];
