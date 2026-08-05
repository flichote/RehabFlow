"use client";

/**
 * TimelineList — 课表时间线列表
 * docs/design/components.md §3.1
 * 按时间升序的课程条目流；含空闲时段标签
 */

import { ScheduleItem } from "./ScheduleItem";
import { EmptySlot } from "./EmptySlot";
import type { ScheduleTimelineItem, FreeSlot } from "@/lib/types";

export function TimelineList({
  items,
  onStart,
  onFinish,
  onRemind,
  onFreeSlotClick,
}: {
  items: ScheduleTimelineItem[];
  onStart?: (id: string) => void;
  onFinish?: (id: string) => void;
  onRemind?: (id: string) => void;
  onFreeSlotClick?: (slot: FreeSlot) => void;
}) {
  if (items.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-center">
        <div className="text-4xl mb-2 opacity-30">📅</div>
        <p className="text-sm text-neutral-400">今日暂无课程</p>
      </div>
    );
  }

  return (
    <div className="space-y-1.5">
      {items.map((item, i) => {
        if (item.kind === "free" && item.free) {
          return (
            <EmptySlot
              key={`free-${i}`}
              slot={item.free}
              onClick={onFreeSlotClick}
            />
          );
        }
        if (item.kind === "course" && item.course) {
          return (
            <ScheduleItem
              key={item.course.id}
              course={item.course}
              onStart={onStart}
              onFinish={onFinish}
              onRemind={onRemind}
            />
          );
        }
        return null;
      })}
    </div>
  );
}
