// app/dashboard/page.tsx
"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@/lib/auth";
import { Button } from "@/components/ui/button";
import Cookies from "js-cookie";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import Image from "next/image";
import { Users, MessageSquare, ArrowRight } from "lucide-react";
import { useRouter } from "next/navigation";

const API_URL = "http://localhost:8080/api";

interface Message {
  speaker: string;
  text: string;
}

interface Conversation {
  _id: string;
  summary: string;
  transcript: Message[];
  createdAt: string;
}

interface Person {
  _id: string;
  name: string;
  relation: string;
  summary: string;
  photo: string;
  created_at: string;
}

export default function DashboardPage() {
  const router = useRouter();
  const { user, logout, isLoading } = useAuth();
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [people, setPeople] = useState<Person[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (user) {
      fetchRecentConversations();
      fetchRecentPeople();
    }
  }, [user]);

  const fetchRecentConversations = async () => {
    const token = Cookies.get("token");
    try {
      const response = await fetch(`${API_URL}/conversations?limit=5`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      if (response.ok) {
        const data = await response.json();
        setConversations(data);
      }
    } catch (error) {
      console.error("Failed to fetch conversations:", error);
    } finally {
      setLoading(false);
    }
  };

  const fetchRecentPeople = async () => {
    const token = Cookies.get("token");
    try {
      const response = await fetch(`${API_URL}/people`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      if (response.ok) {
        const data = await response.json();
        // Take only first 5 people
        setPeople(data.slice(0, 5));
      }
    } catch (error) {
      console.error("Failed to fetch people:", error);
    }
  };

  const getConversationTitle = (conversation: Conversation) => {
    if (!conversation.createdAt) return "Conversation";

    try {
      const date = new Date(conversation.createdAt);
      if (isNaN(date.getTime())) return "Conversation";

      return `Conversation – ${date.toLocaleDateString("en-US", {
        month: "short",
        day: "numeric",
        year: "numeric",
      })}`;
    } catch (error) {
      return "Conversation";
    }
  };

  const formatDate = (dateString: string) => {
    if (!dateString) return "Unknown date";

    try {
      const date = new Date(dateString);

      // Check if date is valid
      if (isNaN(date.getTime())) {
        return "Invalid date";
      }

      const now = new Date();
      const diffTime = Math.abs(now.getTime() - date.getTime());
      const diffMinutes = Math.floor(diffTime / (1000 * 60));
      const diffHours = Math.floor(diffTime / (1000 * 60 * 60));
      const diffDays = Math.floor(diffTime / (1000 * 60 * 60 * 24));

      // Less than 1 hour ago
      if (diffMinutes < 60) {
        if (diffMinutes === 0) return "Just now";
        if (diffMinutes === 1) return "1 minute ago";
        return `${diffMinutes} minutes ago`;
      }

      // Less than 24 hours ago
      if (diffHours < 24) {
        if (diffHours === 1) return "1 hour ago";
        return `${diffHours} hours ago`;
      }

      // Less than 7 days ago
      if (diffDays < 7) {
        if (diffDays === 1) return "Yesterday";
        return `${diffDays} days ago`;
      }

      // Less than 30 days ago
      if (diffDays < 30) {
        const weeks = Math.floor(diffDays / 7);
        if (weeks === 1) return "1 week ago";
        return `${weeks} weeks ago`;
      }

      // Older - show formatted date
      return date.toLocaleDateString("en-US", {
        month: "short",
        day: "numeric",
        year: date.getFullYear() !== now.getFullYear() ? "numeric" : undefined,
      });
    } catch (error) {
      console.error("Error formatting date:", error);
      return "Invalid date";
    }
  };

  if (isLoading || loading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <p>Loading...</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <nav className="bg-white border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 flex justify-between items-center">
          <div className="flex items-center gap-3">
            {user?.profileImage && (
              <div className="relative w-10 h-10">
                <Image
                  src={user.profileImage}
                  alt={user.name}
                  fill
                  className="rounded-full object-cover"
                />
              </div>
            )}
            <h1 className="text-2xl font-bold">
              Welcome, <span className="capitalize">{user?.name}</span>
            </h1>
          </div>
          <div className="flex items-center gap-4">
            <Button onClick={() => router.push("/profile")} variant="outline">
              Profile
            </Button>
            <Button variant="outline">Talk </Button>

            <Button onClick={logout} variant="outline">
              Logout
            </Button>
          </div>
        </div>
      </nav>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Recent Conversations Section */}
        <div className="mb-8">
          <div className="flex justify-between items-center mb-6">
            <h2 className="text-2xl font-semibold flex items-center gap-2">
              Recent Conversations
            </h2>
            <Button
              onClick={() => router.push("/conversations")}
              variant="outline"
            >
              View All
              <ArrowRight size={16} className="ml-2" />
            </Button>
          </div>

          {conversations.length === 0 ? (
            <Card>
              <CardContent className="py-12 text-center">
                <MessageSquare
                  size={48}
                  className="mx-auto mb-4 text-gray-400"
                />
                <p className="text-gray-500 text-lg">No conversations yet</p>
                <p className="text-gray-400 text-sm mt-2">
                  Your conversations will appear here
                </p>
              </CardContent>
            </Card>
          ) : (
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
              {conversations.map((conversation, index) => (
                <Card
                  key={conversation._id}
                  className="cursor-pointer hover:shadow-lg transition-shadow"
                  onClick={() =>
                    router.push(`/conversations/${conversation._id}`)
                  }
                >
                  <CardHeader>
                    <CardTitle className="text-lg line-clamp-1">
                      {getConversationTitle(conversation)}
                    </CardTitle>
                    <CardDescription>
                      {formatDate(conversation.createdAt)}
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <p className="text-sm text-gray-600 line-clamp-3">
                      {conversation.summary}
                    </p>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </div>

        {/* People Section */}
        <div className="mb-8">
          <div className="flex justify-between items-center mb-6">
            <h2 className="text-2xl font-semibold flex items-center gap-2">
              People You Know
            </h2>
            <Button onClick={() => router.push("/people")} variant="outline">
              View All
              <ArrowRight size={16} className="ml-2" />
            </Button>
          </div>

          {people.length === 0 ? (
            <Card>
              <CardContent className="py-12 text-center">
                <Users size={48} className="mx-auto mb-4 text-gray-400" />
                <p className="text-gray-500 text-lg">No people added yet</p>
                <p className="text-gray-400 text-sm mt-2">
                  Add people to help you remember them
                </p>
                <Button
                  onClick={() => router.push("/people/add")}
                  className="mt-4"
                >
                  Add Your First Person
                </Button>
              </CardContent>
            </Card>
          ) : (
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
              {people.map((person) => (
                <Card
                  key={person._id}
                  className="cursor-pointer hover:shadow-lg transition-shadow"
                  onClick={() => router.push(`/people/${person._id}`)}
                >
                  <div className="flex items-center gap-4 p-4">
                    <div className="relative w-16 h-16 flex-shrink-0">
                      <Image
                        src={person.photo}
                        alt={person.name}
                        fill
                        className="rounded-full object-cover"
                      />
                    </div>
                    <div className="flex-1 min-w-0">
                      <h3 className="font-semibold text-lg truncate">
                        {person.name}
                      </h3>
                      <p className="text-sm text-gray-500 capitalize">
                        {person.relation}
                      </p>
                      <p className="text-sm text-gray-600 line-clamp-2 mt-1">
                        {person.summary}
                      </p>
                    </div>
                  </div>
                </Card>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
