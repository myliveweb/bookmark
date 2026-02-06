import { useState } from '#app'
import type { Component } from 'vue'

interface PopoverState {
  isOpen: boolean;
  contentComponent: Component | null;
  props: Record<string, any>;
}

export const usePopoverState = () => {
  return useState<PopoverState>('popover-state', () => ({
    isOpen: false,
    contentComponent: null,
    props: {},
  }));
}

export function openPopover(contentComponent: Component, props: Record<string, any> = {}) {
  const state = usePopoverState();
  state.value = {
    isOpen: true,
    contentComponent,
    props,
  };
}

export function closePopover() {
  const state = usePopoverState();
  state.value.isOpen = false;
}
