// MIT; creates an actual graphics-queue VkDevice, not just enumerating adapters.
#include <vulkan/vulkan.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
int main(int argc, char **argv) {
    if (argc > 2 || (argc == 2 && strcmp(argv[1],"--native"))) return 64;
    int native = argc == 2;
    VkInstance instance;
    VkInstanceCreateInfo ci = {.sType=VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO};
    VkResult r = vkCreateInstance(&ci, NULL, &instance);
    if (r) {fprintf(stderr,"vkCreateInstance=%d\n",r); return 1;}
    uint32_t n=0;
    vkEnumeratePhysicalDevices(instance,&n,NULL);
    VkPhysicalDevice *devices=calloc(n,sizeof(*devices));
    vkEnumeratePhysicalDevices(instance,&n,devices);
    int ok=0;
    for (uint32_t d=0; d<n && !ok; d++) {
        VkPhysicalDeviceProperties props;
        vkGetPhysicalDeviceProperties(devices[d],&props);
        if (native && props.deviceType == VK_PHYSICAL_DEVICE_TYPE_CPU) {
            fprintf(stderr,"NATIVE_ONLY_REFUSED_CPU=%s\n",props.deviceName);
            continue;
        }
        uint32_t count=0;
        vkGetPhysicalDeviceQueueFamilyProperties(devices[d],&count,NULL);
        VkQueueFamilyProperties *queues=calloc(count,sizeof(*queues));
        vkGetPhysicalDeviceQueueFamilyProperties(devices[d],&count,queues);
        for (uint32_t q=0; q<count; q++) {
            if (!(queues[q].queueFlags & VK_QUEUE_GRAPHICS_BIT)) continue;
            float priority=1;
            VkDeviceQueueCreateInfo qi={.sType=VK_STRUCTURE_TYPE_DEVICE_QUEUE_CREATE_INFO,
                .queueFamilyIndex=q,.queueCount=1,.pQueuePriorities=&priority};
            VkDeviceCreateInfo di={.sType=VK_STRUCTURE_TYPE_DEVICE_CREATE_INFO,
                .queueCreateInfoCount=1,.pQueueCreateInfos=&qi};
            VkDevice device;
            r=vkCreateDevice(devices[d],&di,NULL,&device);
            if (r==VK_SUCCESS) {
                VkQueue queue;
                vkGetDeviceQueue(device,q,0,&queue);
                printf("VULKAN_DEVICE_PASS bits=%zu device=%s type=%u api=%u.%u.%u\n",
                    sizeof(void*)*8,props.deviceName,props.deviceType,
                    VK_VERSION_MAJOR(props.apiVersion),VK_VERSION_MINOR(props.apiVersion),VK_VERSION_PATCH(props.apiVersion));
                vkDeviceWaitIdle(device);
                vkDestroyDevice(device,NULL);
                ok=1;
            } else fprintf(stderr,"vkCreateDevice(%s)=%d\n",props.deviceName,r);
            break;
        }
        free(queues);
    }
    free(devices);
    vkDestroyInstance(instance,NULL);
    return ok?0:1;
}
